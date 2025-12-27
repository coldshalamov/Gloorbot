"""
Intelligent Self-Scaling Lowe's Scraper Orchestrator

This orchestrator:
1. Starts with 1-2 worker processes scraping stores
2. Monitors for blocking, crashes, and success rates
3. Gradually increases parallelization until hitting limits
4. Maintains optimal throughput without triggering Akamai
5. Can optionally use OpenAI GPT-4o-mini for scaling decisions

Usage:
    python intelligent_scraper.py --state WA --max-workers 10
    python intelligent_scraper.py --state OR --max-workers 5 --use-ai
"""

import asyncio
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse
import sys

# Optional: OpenAI for intelligent decisions
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️  OpenAI not installed. Run: pip install openai")
    print("    (AI-assisted scaling will be disabled)")


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

    async def start(self):
        """Launch the worker process"""
        store_id = self.store_info['store_id']
        state = self.store_info['state']

        # Create worker-specific output file
        worker_output = self.output_dir / f"worker_{self.worker_id}_store_{store_id}.jsonl"

        # Launch scraper process for this specific store
        cmd = [
            sys.executable,
            "run_single_store.py",
            "--store-id", store_id,
            "--state", state,
            "--output", str(worker_output),
            "--categories", "515"
        ]

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        self.started_at = time.time()
        self.is_alive = True
        self.last_check_time = time.time()

        print(f"✅ Worker {self.worker_id} started for {self.store_info['name']}")

    def check_progress(self):
        """Check if worker is making progress"""
        worker_output = self.output_dir / f"worker_{self.worker_id}_store_{self.store_info['store_id']}.jsonl"

        if not worker_output.exists():
            return 0

        # Count lines (products) in output
        with open(worker_output) as f:
            current_count = sum(1 for _ in f)

        # Detect stalling
        if current_count == self.last_product_count:
            # No progress since last check
            time_stalled = time.time() - self.last_check_time
            if time_stalled > 600:  # 10 minutes without progress
                print(f"⚠️  Worker {self.worker_id} appears stalled (no progress for 10min)")
                return -1  # Signal stall
        else:
            # Progress detected
            self.products_scraped = current_count
            self.last_product_count = current_count
            self.last_check_time = time.time()

        return current_count

    async def stop(self):
        """Gracefully stop the worker"""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=10)
            except asyncio.TimeoutError:
                self.process.kill()
        self.is_alive = False


class IntelligentOrchestrator:
    """Main orchestrator that manages all workers and scaling"""

    def __init__(self, state, max_workers=10, use_ai=False, openai_api_key=None):
        self.state = state
        self.max_workers = max_workers
        self.use_ai = use_ai and HAS_OPENAI
        self.openai_api_key = openai_api_key

        if self.use_ai and openai_api_key:
            openai.api_key = openai_api_key

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

    def load_stores(self):
        """Load stores from LowesMap.txt"""
        lowes_map = Path("LowesMap.txt")
        if not lowes_map.exists():
            print("❌ LowesMap.txt not found!")
            return

        stores = []
        with open(lowes_map) as f:
            for line in f:
                line = line.strip()
                if f'/store/{self.state}-' in line:
                    # Parse store URL
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
        print(f"📋 Loaded {len(self.stores)} {self.state} stores")

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
1. Scale up (add another worker)
2. Scale down (remove a worker)
3. Maintain current level

Consider:
- We want to maximize throughput without triggering anti-bot detection
- Blocking = bad, we need to back off
- Stalling might indicate resource limits
- Gradual scaling is safer than aggressive scaling

Respond with JSON only:
{{"decision": "scale_up|scale_down|maintain", "reason": "brief explanation", "target_workers": number}}"""

            response = await openai.ChatCompletion.acreate(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            ai_decision = json.loads(response.choices[0].message.content)
            print(f"🤖 AI Decision: {ai_decision['decision']} - {ai_decision['reason']}")

            return {
                'recommendation': ai_decision['decision'],
                'reason': f"AI: {ai_decision['reason']}",
                'target_workers': ai_decision['target_workers']
            }

        except Exception as e:
            print(f"⚠️  AI decision failed: {e}")
            return analysis

    async def scale_workers(self, decision):
        """Scale workers up or down based on decision"""
        target = decision['target_workers']

        if target > self.current_workers:
            # Scale up
            to_add = target - self.current_workers
            print(f"📈 Scaling UP: Adding {to_add} worker(s)")

            for i in range(to_add):
                if len(self.workers) >= len(self.stores):
                    print("⚠️  No more stores available")
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

                    # Wait a bit between launches to avoid resource spike
                    await asyncio.sleep(5)

        elif target < self.current_workers:
            # Scale down
            to_remove = self.current_workers - target
            print(f"📉 Scaling DOWN: Removing {to_remove} worker(s)")

            # Stop the most recently added workers
            for i in range(to_remove):
                if self.workers:
                    worker = self.workers.pop()
                    await worker.stop()
                    self.current_workers -= 1

        self.last_scale_time = time.time()

    async def monitoring_loop(self):
        """Main monitoring loop"""
        print("\n" + "="*70)
        print("🚀 INTELLIGENT SCRAPER ORCHESTRATOR")
        print("="*70)
        print(f"State: {self.state}")
        print(f"Max Workers: {self.max_workers}")
        print(f"AI-Assisted: {'Yes' if self.use_ai else 'No'}")
        print(f"Stores to Scrape: {len(self.stores)}")
        print("="*70 + "\n")

        # Start first worker
        if self.stores:
            first_worker = WorkerProcess(0, self.stores[0], self.output_dir)
            await first_worker.start()
            self.workers.append(first_worker)
            self.current_workers = 1
            self.stats['workers_launched'] = 1

        # Main loop
        while self.current_workers > 0 or len(self.workers) < len(self.stores):
            await asyncio.sleep(60)  # Check every minute

            # Analyze performance
            analysis = await self.analyze_performance()

            # Optionally ask AI
            if self.use_ai:
                analysis = await self.ask_ai_for_decision(analysis)

            print(f"\n📊 Status: {analysis['recommendation']} - {analysis['reason']}")
            print(f"   Active Workers: {self.current_workers}/{self.max_workers}")
            print(f"   Total Products: {self.stats['total_products']}")

            # Execute scaling decision
            if analysis['recommendation'] in ['scale_up', 'scale_down']:
                await self.scale_workers(analysis)

            # Aggregate stats
            self.stats['total_products'] = sum(w.products_scraped for w in self.workers if w.is_alive)

            # Check if all stores are done
            completed = sum(1 for w in self.workers if not w.is_alive and w.products_scraped > 0)
            if completed >= len(self.stores):
                print("\n✅ ALL STORES COMPLETED!")
                break

        print("\n" + "="*70)
        print("📊 FINAL STATISTICS")
        print("="*70)
        print(f"Total Products: {self.stats['total_products']}")
        print(f"Workers Launched: {self.stats['workers_launched']}")
        print(f"Runtime: {(time.time() - self.stats['start_time'])/3600:.1f} hours")
        print("="*70)

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
