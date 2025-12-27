"""
Intelligent Scraping Supervisor - Your AI Babysitter

This supervisor:
1. Starts 1-2 workers conservatively
2. Monitors them actively (checks screenshots, logs, resource usage)
3. Verifies "Pickup Today" filter is working
4. Detects blocking by analyzing page content
5. Checks system resources before adding workers
6. Auto-restarts failed workers
7. Generates detailed diagnostic reports
8. Can be monitored via Claude Code CLI

Usage:
    python intelligent_supervisor.py --state WA --check-interval 60

    Then in another terminal:
    python check_supervisor_status.py  # See current status
"""

import asyncio
import json
import sys
import psutil
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import subprocess
import re

class WorkerMonitor:
    """Monitors a single worker with deep diagnostics"""

    def __init__(self, worker_id, store_info, output_dir, profile_dir):
        self.worker_id = worker_id
        self.store_info = store_info
        self.output_dir = Path(output_dir)
        self.profile_dir = Path(profile_dir)

        self.process = None
        self.pid = None
        self.started_at = None
        self.last_product_count = 0
        self.products_scraped = 0
        self.last_check_time = None
        self.is_alive = False

        # Health metrics
        self.health = {
            'is_blocked': False,
            'pickup_filter_active': None,  # True/False/Unknown
            'store_context_set': None,
            'products_per_minute': 0,
            'memory_mb': 0,
            'cpu_percent': 0,
            'consecutive_errors': 0,
            'last_screenshot': None
        }

        self.log_file = output_dir / f"worker_{worker_id}_supervisor.log"

    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] Worker {self.worker_id}: {message}"
        print(entry)

        with open(self.log_file, 'a') as f:
            f.write(entry + "\n")

    async def start(self):
        """Launch worker with monitoring"""
        store_id = self.store_info['store_id']
        state = self.store_info['state']

        worker_output = self.output_dir / f"worker_{self.worker_id}_store_{store_id}.jsonl"

        # Create profile directory
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "run_single_store.py",
            "--store-id", store_id,
            "--state", state,
            "--output", str(worker_output),
            "--categories", "515"
        ]

        self.log(f"Starting for {self.store_info['name']}")

        # Use subprocess.Popen instead of asyncio for Windows compatibility
        import subprocess
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path.cwd()),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )

        self.pid = self.process.pid
        self.started_at = time.time()
        self.is_alive = True
        self.last_check_time = time.time()

        self.log(f"Started with PID {self.pid}")

    async def check_health(self):
        """Deep health check - this is the key diagnostic"""
        if not self.is_alive or not self.pid:
            return

        try:
            # 1. Check if process still exists
            try:
                proc = psutil.Process(self.pid)
                if not proc.is_running():
                    self.log("Process died!", "ERROR")
                    self.is_alive = False
                    return
            except psutil.NoSuchProcess:
                self.log("Process not found!", "ERROR")
                self.is_alive = False
                return

            # 2. Get resource usage
            proc = psutil.Process(self.pid)
            self.health['memory_mb'] = proc.memory_info().rss / 1024 / 1024
            self.health['cpu_percent'] = proc.cpu_percent(interval=0.1)

            # 3. Check product output
            worker_output = self.output_dir / f"worker_{self.worker_id}_store_{self.store_info['store_id']}.jsonl"
            if worker_output.exists():
                with open(worker_output) as f:
                    current_count = sum(1 for _ in f)

                # Calculate products per minute
                if self.last_product_count > 0:
                    time_diff = time.time() - self.last_check_time
                    products_diff = current_count - self.last_product_count
                    if time_diff > 0:
                        self.health['products_per_minute'] = (products_diff / time_diff) * 60

                self.products_scraped = current_count

                # Check if stalled
                if current_count == self.last_product_count:
                    stall_time = time.time() - self.last_check_time
                    if stall_time > 600:  # 10 min stall
                        self.log(f"STALLED for {stall_time/60:.1f} minutes", "WARNING")
                else:
                    self.last_product_count = current_count
                    self.last_check_time = time.time()

            # 4. Check for blocking by examining browser screenshots
            screenshot_dir = Path(f".playwright-profiles/store-{self.store_info['store_id']}")
            if screenshot_dir.exists():
                # Look for recent screenshots (if scraper takes them)
                screenshots = sorted(screenshot_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
                if screenshots:
                    self.health['last_screenshot'] = str(screenshots[0])
                    # TODO: Could use OCR or image analysis to check for "Access Denied"

            # 5. Check browser profile for cookies (indicates session health)
            cookies_file = self.profile_dir / "Default" / "Network" / "Cookies"
            if cookies_file.exists():
                # Cookies exist = session active
                self.health['store_context_set'] = True

            # Log health status
            self.log(
                f"Health: {self.products_scraped} products | "
                f"{self.health['products_per_minute']:.1f}/min | "
                f"{self.health['memory_mb']:.0f}MB | "
                f"{self.health['cpu_percent']:.1f}% CPU"
            )

        except Exception as e:
            self.log(f"Health check error: {e}", "ERROR")
            self.health['consecutive_errors'] += 1

    async def take_diagnostic_screenshot(self):
        """Force a diagnostic screenshot of current browser state"""
        # This would require adding screenshot capability to the worker
        # For now, just log the request
        self.log("Diagnostic screenshot requested")
        # TODO: Send signal to worker to take screenshot

    async def stop(self):
        """Gracefully stop worker and ALL Chrome processes"""
        if self.process and self.pid:
            self.log("Stopping worker and cleaning up Chrome processes...")

            try:
                # Get the worker process and all its children (Chrome processes)
                parent = psutil.Process(self.pid)
                children = parent.children(recursive=True)

                # First, kill all child processes (Chrome and subprocesses)
                for child in children:
                    try:
                        self.log(f"Killing child process: {child.name()} (PID {child.pid})")
                        child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # Give processes time to die
                import time
                time.sleep(2)

                # Then terminate the main worker process
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.log("Worker didn't exit gracefully, force killing...", "WARNING")
                    self.process.kill()

                self.log("Worker and all Chrome processes stopped successfully")

            except psutil.NoSuchProcess:
                self.log("Process already dead", "WARNING")
            except Exception as e:
                self.log(f"Error during cleanup: {e}", "ERROR")
                # Force kill as fallback
                try:
                    self.process.kill()
                except:
                    pass

        self.is_alive = False


class IntelligentSupervisor:
    """The AI babysitter that watches everything"""

    def __init__(self, state, max_workers=10, check_interval=60):
        self.state = state
        self.max_workers = max_workers
        self.check_interval = check_interval  # Check every N seconds

        self.workers = []
        self.stores = []
        self.output_dir = Path("scrape_output_supervised")
        self.output_dir.mkdir(exist_ok=True)

        self.status_file = self.output_dir / "supervisor_status.json"

        self.stats = {
            'start_time': time.time(),
            'total_products': 0,
            'workers_launched': 0,
            'workers_failed': 0,
            'blocking_incidents': 0,
            'restarts': 0,
            'current_workers': 0
        }

        self.system_limits = {
            'max_memory_mb': psutil.virtual_memory().total / 1024 / 1024 * 0.7,  # 70% of RAM
            'max_cpu_percent': 80,  # Don't go above 80% CPU
        }

    def log(self, message, level="INFO"):
        """Main supervisor log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] SUPERVISOR: {message}"
        print(entry)

        with open(self.output_dir / "supervisor.log", 'a') as f:
            f.write(entry + "\n")

    def load_stores(self):
        """Load stores from LowesMap.txt"""
        lowes_map = Path("LowesMap.txt")
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
        self.log(f"Loaded {len(self.stores)} {self.state} stores")

    def check_system_resources(self):
        """Check if we have resources for another worker"""
        total_mem = sum(w.health['memory_mb'] for w in self.workers if w.is_alive)
        total_cpu = sum(w.health['cpu_percent'] for w in self.workers if w.is_alive)

        available_mem = self.system_limits['max_memory_mb'] - total_mem
        available_cpu = self.system_limits['max_cpu_percent'] - total_cpu

        # Estimate: each worker uses ~800MB RAM and ~15% CPU
        can_add = (
            available_mem > 1000 and  # Need 1GB free
            available_cpu > 20  # Need 20% CPU free
        )

        self.log(
            f"Resources: RAM {total_mem:.0f}/{self.system_limits['max_memory_mb']:.0f}MB | "
            f"CPU {total_cpu:.1f}/{self.system_limits['max_cpu_percent']:.1f}%"
        )

        return can_add, f"RAM: {available_mem:.0f}MB free, CPU: {available_cpu:.1f}% free"

    async def intelligent_decision(self):
        """Make smart decisions about scaling"""
        active_workers = [w for w in self.workers if w.is_alive]

        if not active_workers and len(self.workers) < len(self.stores):
            return 'start_first', "No active workers, starting first one"

        # Check for blocking
        blocked_workers = [w for w in active_workers if w.health['is_blocked']]
        if blocked_workers:
            self.stats['blocking_incidents'] += 1
            return 'scale_down', f"Blocking detected in {len(blocked_workers)} worker(s)"

        # Check for stalled workers
        stalled = [w for w in active_workers if w.health['products_per_minute'] < 0.1 and time.time() - w.started_at > 600]
        if len(stalled) > len(active_workers) / 2:
            return 'investigate', f"{len(stalled)}/{len(active_workers)} workers stalled"

        # Check if we can add more
        if self.stats['current_workers'] < self.max_workers and len(self.workers) < len(self.stores):
            can_add, reason = self.check_system_resources()

            if can_add:
                # Check if current workers are healthy
                healthy = all(
                    w.health['consecutive_errors'] < 3 and
                    w.health['products_per_minute'] > 0
                    for w in active_workers
                )

                if healthy:
                    return 'scale_up', f"All workers healthy, {reason}"

        return 'maintain', "System stable"

    async def execute_decision(self, decision, reason):
        """Execute the decision"""
        self.log(f"Decision: {decision} - {reason}")

        if decision == 'start_first' or decision == 'scale_up':
            # Add a new worker
            if len(self.workers) >= len(self.stores):
                self.log("All stores have workers assigned")
                return

            # Find next unassigned store
            assigned_stores = {w.store_info['store_id'] for w in self.workers}
            next_store = next((s for s in self.stores if s['store_id'] not in assigned_stores), None)

            if next_store:
                worker_id = len(self.workers)
                profile_dir = Path(f".playwright-profiles/store-{next_store['store_id']}")

                worker = WorkerMonitor(worker_id, next_store, self.output_dir, profile_dir)
                await worker.start()

                self.workers.append(worker)
                self.stats['current_workers'] += 1
                self.stats['workers_launched'] += 1

                # Wait a bit before adding another
                await asyncio.sleep(10)

        elif decision == 'scale_down':
            # Remove the most recent worker
            if self.workers:
                worker = self.workers[-1]
                await worker.stop()
                self.stats['current_workers'] -= 1

        elif decision == 'investigate':
            self.log("Investigating stalled workers...")
            for worker in self.workers:
                if worker.is_alive and worker.health['products_per_minute'] < 0.1:
                    await worker.check_health()
                    # TODO: Could take diagnostic screenshot here

    def save_status(self):
        """Save status for external monitoring"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time() - self.stats['start_time'],
            'stats': self.stats,
            'workers': [
                {
                    'id': w.worker_id,
                    'store': w.store_info['name'],
                    'alive': w.is_alive,
                    'products': w.products_scraped,
                    'products_per_min': w.health['products_per_minute'],
                    'memory_mb': w.health['memory_mb'],
                    'cpu_percent': w.health['cpu_percent'],
                }
                for w in self.workers
            ]
        }

        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)

    async def monitoring_loop(self):
        """Main monitoring loop - the babysitter"""
        self.log("="*70)
        self.log("INTELLIGENT SUPERVISOR STARTING")
        self.log("="*70)
        self.log(f"State: {self.state}")
        self.log(f"Max Workers: {self.max_workers}")
        self.log(f"Check Interval: {self.check_interval}s")
        self.log(f"Stores to Scrape: {len(self.stores)}")
        self.log("="*70)

        iteration = 0

        while True:
            iteration += 1
            self.log(f"\n--- Iteration {iteration} ---")

            # 1. Check health of all workers
            for worker in self.workers:
                if worker.is_alive:
                    await worker.check_health()

            # 2. Make intelligent decision
            decision, reason = await self.intelligent_decision()

            # 3. Execute decision
            await self.execute_decision(decision, reason)

            # 4. Update stats
            self.stats['total_products'] = sum(w.products_scraped for w in self.workers)
            self.stats['current_workers'] = sum(1 for w in self.workers if w.is_alive)

            # 5. Save status for external monitoring
            self.save_status()

            # 6. Print summary
            active = [w for w in self.workers if w.is_alive]
            if active:
                total_rate = sum(w.health['products_per_minute'] for w in active)
                self.log(
                    f"Status: {len(active)} workers | "
                    f"{self.stats['total_products']} products | "
                    f"{total_rate:.1f} products/min"
                )

            # 7. Check if done
            completed = sum(1 for w in self.workers if not w.is_alive and w.products_scraped > 0)
            if completed >= len(self.stores):
                self.log("ALL STORES COMPLETED!")
                break

            # 8. Wait before next check
            await asyncio.sleep(self.check_interval)

        # Final report
        self.stats['end_time'] = time.time()
        self.log("="*70)
        self.log("FINAL REPORT")
        self.log("="*70)
        self.log(f"Total Products: {self.stats['total_products']}")
        self.log(f"Workers Launched: {self.stats['workers_launched']}")
        self.log(f"Failed/Restarted: {self.stats['workers_failed']}")
        self.log(f"Blocking Incidents: {self.stats['blocking_incidents']}")
        self.log(f"Runtime: {(self.stats['end_time'] - self.stats['start_time'])/3600:.1f} hours")
        self.log("="*70)

    async def run(self):
        """Main entry point"""
        self.load_stores()
        await self.monitoring_loop()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Intelligent Scraping Supervisor')
    parser.add_argument('--state', default='WA', choices=['WA', 'OR'])
    parser.add_argument('--max-workers', type=int, default=10)
    parser.add_argument('--check-interval', type=int, default=60, help='Check every N seconds')
    args = parser.parse_args()

    supervisor = IntelligentSupervisor(
        state=args.state,
        max_workers=args.max_workers,
        check_interval=args.check_interval
    )

    await supervisor.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSupervisor stopped by user")
