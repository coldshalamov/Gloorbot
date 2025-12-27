import asyncio
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse
import sys
import signal
import atexit
import logging

# Ensure psutil is available for safe killing
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("⚠️  Use 'pip install psutil' for safer process management")

# Optional: OpenAI for intelligent decisions
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️  OpenAI not installed. Run: pip install openai")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("scraper_orchestrator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("Orchestrator")

def kill_proc_tree(pid, including_parent=True):
    """Recursively kill a process tree"""
    if not HAS_PSUTIL:
        try:
            if sys.platform == 'win32':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import os
                os.kill(pid, signal.SIGTERM)
        except:
            pass
        return

    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        if including_parent:
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass

class WorkerProcess:
    """Manages a single scraper worker process"""

    def __init__(self, worker_id, store_info, output_dir):
        self.worker_id = worker_id
        self.store_info = store_info
        self.output_dir = Path(output_dir)
        self.process = None
        self.started_at = None
        self.products_scraped = 0
        self.last_product_count = 0
        self.last_check_time = None
        self.is_alive = False
        self.is_blocked = False
        self.error_count = 0
        self.last_category_idx = 0

    async def start(self):
        """Launch the worker process"""
        store_id = self.store_info['store_id']
        state = self.store_info['state']

        # Create worker-specific output file
        worker_output = self.output_dir / f"worker_{self.worker_id}_store_{store_id}.jsonl"

        # Check for checkpoint
        check_file = Path("scrape_logs") / f"checkpoint_{store_id}.txt"
        start_idx = 0
        if check_file.exists():
            try:
                start_idx = int(check_file.read_text().strip())
                log.info(f"Resuming worker {self.worker_id} for {store_id} from index {start_idx}")
            except:
                pass

        # Launch scraper process for this specific store
        # We use run_single_store.py which imports main.py
        cmd = [
            sys.executable,
            "run_single_store.py",
            "--store-id", store_id,
            "--state", state,
            "--output", str(worker_output),
            "--start-idx", str(start_idx),
            "--check-file", str(check_file)
        ]

        # Redirect output to log file to avoid deadlock
        log_dir = Path("scrape_logs")
        log_dir.mkdir(exist_ok=True)
        self.log_file = open(log_dir / f"worker_{self.worker_id}_{store_id}.log", "w", encoding='utf-8')

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=self.log_file,
            stderr=asyncio.subprocess.STDOUT
        )

        self.started_at = time.time()
        self.is_alive = True
        self.last_check_time = time.time()

        log.info(f"Worker {self.worker_id} started for {store_id} (PID: {self.process.pid})")

    def check_progress(self):
        """Check if worker is making progress"""
        if self.process and self.process.returncode is not None:
            self.is_alive = False
            return 0

        # Check line counts in output
        worker_output = self.output_dir / f"worker_{self.worker_id}_store_{self.store_info['store_id']}.jsonl"

        if not worker_output.exists():
            return 0

        try:
            with open(worker_output, 'rb') as f:
                current_count = sum(1 for _ in f)
        except:
            return 0

        # Detect stalling
        if current_count == self.last_product_count:
            # No progress since last check
            time_stalled = time.time() - self.last_check_time
            if time_stalled > 600:  # 10 minutes without progress
                log.warning(f"Worker {self.worker_id} appears stalled (no progress for 10min)")
                return -1  # Signal stall
        else:
            # Progress detected
            self.products_scraped = current_count
            self.last_product_count = current_count
            self.last_check_time = time.time()

        return current_count

    async def stop(self):
        """Gracefully stop the worker and kill children"""
        if self.process:
            pid = self.process.pid
            log.info(f"Stopping worker {self.worker_id} (PID: {pid})")
            kill_proc_tree(pid)
            
        self.is_alive = False


class IntelligentOrchestrator:
    """Main orchestrator that manages all workers and scaling"""

    def __init__(self, state, max_workers=10, use_ai=False, openai_api_key=None):
        self.state = state
        self.max_workers = max_workers
        self.use_ai = use_ai and HAS_OPENAI
        self.openai_api_key = openai_api_key
        # Only enable AI if requested, library present, AND key provided
        self.use_ai = use_ai and HAS_OPENAI and (openai_api_key is not None)
        self.running = True

        if self.use_ai:
            openai.api_key = openai_api_key
            log.info("create_orchestrator: AI Scaling ENABLED 🤖")
        else:
            log.info("create_orchestrator: AI Scaling DISABLED (Missing key or library)")

        self.workers = []
        self.stores = []
        self.output_dir = Path("scrape_output_parallel")
        self.output_dir.mkdir(exist_ok=True)

        self.stats = {
            'total_products': 0,
            'workers_launched': 0,
            'blocking_incidents': 0,
            'crashes': 0,
            'start_time': time.time()
        }

        # Scaling parameters
        self.current_workers = 0
        self.target_workers = 1  # Start conservatively
        self.scale_up_interval = 300  # Try scaling every 5 minutes
        self.last_scale_time = time.time()
        
        # Register cleanup
        atexit.register(self.force_cleanup)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        log.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.force_cleanup()
        sys.exit(0)

    def force_cleanup(self):
        """Kill all workers immediately"""
        if not self.workers:
            return
            
        log.info("🧹 Performing cleanup of child processes...")
        for w in self.workers:
            if w.process:
                kill_proc_tree(w.process.pid)
        self.workers = []
        log.info("Cleanup complete.")

    def load_stores(self):
        """Load stores from LowesMap_Final_Pruned.txt (or LowesMap.txt as fallback)"""
        # Try finding the map in various locations
        possible_paths = [
            Path("LowesMap_Final_Pruned.txt"),
            Path("LowesMap.txt")
        ]
        
        lowes_map = None
        for p in possible_paths:
            if p.exists():
                lowes_map = p
                break
        
        if not lowes_map:
            log.error("LowesMap not found!")
            return

        stores = []
        with open(lowes_map) as f:
            for line in f:
                line = line.strip()
                if f'/store/{self.state}-' in line:
                    import re
                    match = re.search(r'/store/([A-Z]{2})-([^/]+)/(\d+)', line)
                    if match:
                        state, city, store_id = match.groups()
                        stores.append({
                            'url': line,
                            'store_id': store_id,
                            'city': city.replace('-', ' '),
                            'state': state,
                            'name': f"{city}, {state} (#{store_id})"
                        })

        self.stores = stores
        log.info(f"Loaded {len(self.stores)} {self.state} stores from {lowes_map}")

    async def analyze_performance(self):
        """Analyze current performance and decide on scaling"""
        active_workers = [w for w in self.workers if w.is_alive]

        if not active_workers:
            return {
                'recommendation': 'start_first_worker',
                'reason': 'No active workers'
            }

        # Check each worker's progress
        total_products = 0
        stalled_workers = 0
        blocked_workers = 0

        for worker in active_workers:
            progress = worker.check_progress()
            if progress < 0:
                stalled_workers += 1
            elif progress > 0:
                total_products += progress

            if worker.is_blocked:
                blocked_workers += 1

        # Calculate metrics
        uptime = time.time() - self.stats['start_time']
        products_per_minute = (total_products / uptime) * 60 if uptime > 0 else 0

        # Scaling logic
        if blocked_workers > 0:
            return {
                'recommendation': 'scale_down',
                'reason': f'{blocked_workers} worker(s) blocked - reduce load',
                'target_workers': max(1, self.current_workers - 1)
            }

        if stalled_workers > len(active_workers) / 2:
            return {
                'recommendation': 'maintain',
                'reason': f'{stalled_workers} workers stalled - monitor before scaling',
                'target_workers': self.current_workers
            }

        # If everything is healthy and we're under max, consider scaling up
        if self.current_workers < self.max_workers:
            # Check if enough time has passed since last scale
            if time.time() - self.last_scale_time > self.scale_up_interval:
                return {
                    'recommendation': 'scale_up',
                    'reason': f'All workers healthy, {products_per_minute:.1f} products/min',
                    'target_workers': min(self.max_workers, self.current_workers + 1)
                }

        return {
            'recommendation': 'maintain',
            'reason': f'Stable at {self.current_workers} workers, {products_per_minute:.1f} products/min',
            'target_workers': self.current_workers
        }

    async def ask_ai_for_decision(self, analysis):
        """Use GPT-4o-mini to make scaling decisions"""
        if not self.use_ai:
            return analysis

        try:
            # Prepare context for AI
            active_workers = [w for w in self.workers if w.is_alive]
            worker_stats = []
            for w in active_workers:
                worker_stats.append({
                    'worker_id': w.worker_id,
                    'store': w.store_info['name'],
                    'products': w.products_scraped,
                    'runtime_min': (time.time() - w.started_at) / 60,
                    'is_blocked': w.is_blocked
                })

            prompt = f"""You are managing a web scraping operation with the following status:

Current Workers: {self.current_workers}
Max Workers: {self.max_workers}
Total Products Scraped: {self.stats['total_products']}
Blocking Incidents: {self.stats['blocking_incidents']}
Worker Stats: {json.dumps(worker_stats, indent=2)}

Automated Analysis: {json.dumps(analysis, indent=2)}

Should we:
1. Scale up (add another worker) - ONLY if no blocks and stable run
2. Scale down (remove a worker) - IF blocked or errors high
3. Maintain current level

Respond with JSON only:
{{"decision": "scale_up|scale_down|maintain", "reason": "brief explanation", "target_workers": number}}"""

            response = await openai.ChatCompletion.acreate(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            ai_decision = json.loads(response.choices[0].message.content)
            log.info(f"AI Decision: {ai_decision['decision']} - {ai_decision['reason']}")

            return {
                'recommendation': ai_decision['decision'],
                'reason': f"AI: {ai_decision['reason']}",
                'target_workers': int(ai_decision.get('target_workers', self.current_workers))
            }

        except Exception as e:
            log.warning(f"AI decision failed: {e}")
            return analysis

    async def scale_workers(self, decision):
        """Scale workers up or down based on decision"""
        target = decision['target_workers']

        if target > self.current_workers:
            # Scale up
            to_add = target - self.current_workers
            log.info(f"Scaling UP: Adding {to_add} worker(s)")

            for i in range(to_add):
                if len(self.workers) >= len(self.stores):
                    log.warning("No more stores available")
                    break

                # Get next unassigned store
                assigned_stores = {w.store_info['store_id'] for w in self.workers}
                next_store = next((s for s in self.stores if s['store_id'] not in assigned_stores), None)

                if next_store:
                    worker_id = len(self.workers)
                    worker = WorkerProcess(worker_id, next_store, self.output_dir)
                    await worker.start()
                    self.workers.append(worker)
                    self.current_workers += 1
                    self.stats['workers_launched'] += 1
                    await asyncio.sleep(5)

        elif target < self.current_workers:
            # Scale down
            to_remove = self.current_workers - target
            log.info(f"Scaling DOWN: Removing {to_remove} worker(s)")

            for i in range(to_remove):
                if self.workers:
                    worker = self.workers.pop()
                    await worker.stop()
                    self.current_workers -= 1

        self.last_scale_time = time.time()

    async def monitoring_loop(self):
        """Main monitoring loop"""
        log.info("="*70)
        log.info("INTELLIGENT SCRAPER ORCHESTRATOR")
        log.info("="*70)
        log.info(f"State: {self.state}")
        log.info(f"Stores to Scrape: {len(self.stores)}")
        
        # Start first worker
        if self.stores:
            first_worker = WorkerProcess(0, self.stores[0], self.output_dir)
            await first_worker.start()
            self.workers.append(first_worker)
            self.current_workers = 1
            self.stats['workers_launched'] = 1

        # Main loop
        while self.running and (self.current_workers > 0 or len(self.workers) < len(self.stores)):
            try:
                await asyncio.sleep(60)  # Check every minute

                # Analyze performance
                analysis = await self.analyze_performance()

                # Optionally ask AI
                if self.use_ai:
                    analysis = await self.ask_ai_for_decision(analysis)

                log.info(f"Status: {analysis['recommendation']} - {analysis['reason']}")
                log.info(f"   Active Workers: {self.current_workers}/{self.max_workers}")
                log.info(f"   Total Products: {self.stats['total_products']}")

                # Execute scaling decision
                if analysis['recommendation'] in ['scale_up', 'scale_down']:
                    await self.scale_workers(analysis)

                # Aggregate stats
                self.stats['total_products'] = sum(w.products_scraped for w in self.workers if w.is_alive)

                # Check if all stores are done
                completed = sum(1 for w in self.workers if not w.is_alive and w.products_scraped > 0)
                if completed >= len(self.stores):
                    log.info("ALL STORES COMPLETED!")
                    break
            except Exception as e:
                log.error(f"Error in monitoring loop: {e}")
                # Don't crash the orchestrator, just wait and retry
                await asyncio.sleep(30)

        log.info("="*70)
        log.info("FINAL STATISTICS")
        log.info(f"Total Products: {self.stats['total_products']}")
        log.info(f"Runtime: {(time.time() - self.stats['start_time'])/3600:.1f} hours")
        log.info("="*70)
        self.force_cleanup()

    async def run(self):
        """Main entry point"""
        self.load_stores()
        await self.monitoring_loop()


async def main():
    parser = argparse.ArgumentParser(description='Intelligent Self-Scaling Lowe\'s Scraper')
    parser.add_argument('--state', default='WA', choices=['WA', 'OR'], help='State to scrape')
    parser.add_argument('--max-workers', type=int, default=10, help='Maximum parallel workers')
    parser.add_argument('--use-ai', action='store_true', help='Use OpenAI for scaling decisions')
    parser.add_argument('--openai-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')

    args = parser.parse_args()

    # Get OpenAI key from args or environment
    import os
    openai_key = args.openai_key or os.getenv('OPENAI_API_KEY')

    orchestrator = IntelligentOrchestrator(
        state=args.state,
        max_workers=args.max_workers,
        use_ai=args.use_ai,
        openai_api_key=openai_key
    )

    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
