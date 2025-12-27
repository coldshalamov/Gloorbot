"""
Lowe's Scraper - Orchestrator
Manages multiple worker processes for parallel store scraping.
"""
import asyncio
import subprocess
import sys
import time
import signal
import atexit
import logging
import re
from pathlib import Path
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("orchestrator.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Try to import psutil for better process management
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    log.warning("psutil not installed - process cleanup may be incomplete")


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
    def __init__(self, worker_id, store_info, base_dir):
        self.worker_id = worker_id
        self.store_info = store_info
        self.base_dir = Path(base_dir)
        self.process = None
        self.started_at = None
        self.products_scraped = 0
        self.last_product_count = 0
        self.last_check_time = None
        self.is_alive = False
        self.log_file = None

    async def start(self):
        """Launch the worker process"""
        store_id = self.store_info['store_id']
        
        output_file = self.base_dir / "output" / f"store_{store_id}.jsonl"
        checkpoint_file = self.base_dir / "checkpoints" / f"store_{store_id}.txt"
        log_path = self.base_dir / "logs" / f"worker_{self.worker_id}_{store_id}.log"
        
        # Check for existing checkpoint
        start_idx = 0
        if checkpoint_file.exists():
            try:
                start_idx = int(checkpoint_file.read_text().strip())
                log.info(f"Worker {self.worker_id}: Resuming store {store_id} from index {start_idx}")
            except:
                pass

        cmd = [
            sys.executable,
            str(self.base_dir / "scraper.py"),
            "--store-id", store_id,
            "--state", self.store_info['state'],
            "--output", str(output_file),
            "--checkpoint", str(checkpoint_file),
            "--urls-file", str(self.base_dir / "urls.txt")
        ]

        self.log_file = open(log_path, "w", encoding='utf-8')

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

        # Check output file size
        store_id = self.store_info['store_id']
        output_file = self.base_dir / "output" / f"store_{store_id}.jsonl"
        
        try:
            if output_file.exists():
                lines = sum(1 for _ in open(output_file, encoding='utf-8'))
                new_products = lines - self.last_product_count
                self.last_product_count = lines
                self.products_scraped = lines
                return new_products
        except:
            pass
        return 0

    async def stop(self):
        """Stop the worker process"""
        if self.process:
            kill_proc_tree(self.process.pid)
            self.is_alive = False
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass


class Orchestrator:
    def __init__(self, base_dir, states, max_workers=5):
        self.base_dir = Path(base_dir)
        self.states = [s.strip().upper() for s in states.split(',')]
        self.max_workers = max_workers
        self.workers = []
        self.stores = []
        self.store_queue = []
        self.completed_stores = set()
        self.running = True
        
        # Register cleanup
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        log.info("Shutdown signal received")
        self.running = False
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Clean up all worker processes"""
        log.info("Cleaning up workers...")
        for w in self.workers:
            if w.process:
                kill_proc_tree(w.process.pid)
        self.workers = []
        log.info("Cleanup complete")

    def load_stores(self):
        """Load stores from urls.txt"""
        urls_file = self.base_dir / "urls.txt"
        
        if not urls_file.exists():
            log.error("urls.txt not found!")
            return

        stores = []
        with open(urls_file) as f:
            for line in f:
                line = line.strip()
                for st in self.states:
                    if f'/store/{st}-' in line:
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
                        break

        self.stores = stores
        self.store_queue = list(stores)
        log.info(f"Loaded {len(self.stores)} stores for states {self.states}")

    async def start_worker(self, store_info):
        """Start a new worker for a store"""
        worker_id = len(self.workers)
        worker = WorkerProcess(worker_id, store_info, self.base_dir)
        await worker.start()
        self.workers.append(worker)
        return worker

    async def run(self):
        """Main orchestration loop"""
        self.load_stores()
        
        if not self.stores:
            log.error("No stores to scrape!")
            return

        log.info("=" * 60)
        log.info("LOWES SCRAPER ORCHESTRATOR")
        log.info("=" * 60)
        log.info(f"States: {self.states}")
        log.info(f"Stores: {len(self.stores)}")
        log.info(f"Max Workers: {self.max_workers}")
        log.info("=" * 60)

        # Start initial workers
        while self.store_queue and len(self.workers) < self.max_workers:
            store = self.store_queue.pop(0)
            await self.start_worker(store)
            await asyncio.sleep(2)

        # Main loop
        while self.running:
            await asyncio.sleep(60)  # Check every minute
            
            if not self.running:
                break

            # Check worker status
            total_products = 0
            active_workers = 0

            for worker in self.workers:
                progress = worker.check_progress()
                total_products += worker.products_scraped
                
                if worker.is_alive:
                    active_workers += 1
                elif worker.process and worker.process.returncode is not None:
                    # Worker finished
                    store_id = worker.store_info['store_id']
                    self.completed_stores.add(store_id)
                    log.info(f"Worker {worker.worker_id} completed store {store_id}")
                    
                    # Start new worker if queue has stores
                    if self.store_queue:
                        next_store = self.store_queue.pop(0)
                        new_worker = WorkerProcess(len(self.workers), next_store, self.base_dir)
                        await new_worker.start()
                        self.workers.append(new_worker)

            log.info(f"Status: {active_workers}/{len(self.workers)} workers active, {total_products} total products, {len(self.completed_stores)}/{len(self.stores)} stores done")

            # Check if all done
            if len(self.completed_stores) >= len(self.stores):
                log.info("ALL STORES COMPLETE!")
                break

        self.cleanup()
        log.info(f"Final: {len(self.completed_stores)} stores completed")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="WA,OR", help="Comma-separated states (e.g. WA,OR)")
    parser.add_argument("--workers", type=int, default=5, help="Max parallel workers")
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent
    orchestrator = Orchestrator(base_dir, args.state, args.workers)
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
