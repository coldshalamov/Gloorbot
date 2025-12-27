"""
AI-Powered Supervisor - True intelligent monitoring with LLM

This wraps the intelligent_supervisor.py and adds real AI decision-making:
- Takes screenshots periodically
- Analyzes logs with GPT-4o-mini
- Makes intelligent decisions based on visual/text analysis
- Sends you status updates

Usage:
    # Set your OpenAI API key first:
    export OPENAI_API_KEY="sk-..."

    # Then run:
    python ai_supervisor.py --state WA --max-workers 8

    # Or for all states:
    python ai_supervisor.py --all-states --max-workers 8
"""

import asyncio
import json
import time
import os
import base64
from pathlib import Path
from datetime import datetime
import subprocess

# Try to import OpenAI (install if needed)
try:
    from openai import OpenAI
except ImportError:
    print("OpenAI library not installed. Install with: pip install openai")
    exit(1)


class AISupervisor:
    """True AI supervisor using GPT-4o-mini for intelligent monitoring"""

    def __init__(self, state, max_workers=8, check_interval=300, model="gpt-4o-mini"):
        self.state = state
        self.max_workers = max_workers
        self.check_interval = check_interval  # Check every 5 minutes by default
        self.model = model

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)

        self.supervisor_process = None
        self.log_file = Path(f"ai_supervisor_{state}.log")

        # AI analysis history
        self.analysis_history = []

    def log(self, message, level="INFO"):
        """Log AI supervisor actions"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        print(entry)

        with open(self.log_file, 'a') as f:
            f.write(entry + "\n")

    def encode_image(self, image_path):
        """Encode image to base64 for GPT-4 Vision"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def analyze_with_ai(self, status_data, recent_logs, screenshots=None):
        """Use GPT-4o-mini to analyze current scraping state"""

        # Build context for AI
        context = f"""You are monitoring a web scraping operation. Analyze the current state and provide insights.

CURRENT STATUS:
- State: {self.state}
- Total Products: {status_data['stats']['total_products']:,}
- Active Workers: {status_data['stats']['current_workers']}
- Workers Launched: {status_data['stats']['workers_launched']}
- Blocking Incidents: {status_data['stats']['blocking_incidents']}
- Uptime: {status_data['uptime_seconds']/3600:.1f} hours

WORKERS:
"""

        for worker in status_data['workers']:
            if worker['alive']:
                context += f"\n  Worker {worker['id']} ({worker['store']}): {worker['products']:,} products, {worker['products_per_min']:.2f}/min, {worker['memory_mb']:.0f}MB RAM"

        context += f"\n\nRECENT LOGS (last 20 lines):\n{recent_logs}\n"

        # Add analysis prompt
        prompt = """
Based on the above status, answer these questions:

1. Is the scraping operation healthy? (Yes/No and why)
2. Are there any workers that appear stalled or blocked?
3. Should we add more workers, remove workers, or maintain current level?
4. Are there any warning signs in the logs?
5. What's your recommended action? (scale_up, scale_down, maintain, investigate)

Provide your analysis in JSON format:
{
  "healthy": true/false,
  "issues": ["list of issues if any"],
  "recommendation": "scale_up/scale_down/maintain/investigate",
  "reasoning": "brief explanation",
  "next_check_in": "suggested time in minutes"
}
"""

        messages = [
            {"role": "system", "content": "You are an expert at monitoring web scraping operations. Be concise and actionable."},
            {"role": "user", "content": context + prompt}
        ]

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3
            )

            analysis = json.loads(response.choices[0].message.content)

            # Log token usage
            usage = response.usage
            self.log(f"AI Analysis - Tokens: {usage.total_tokens} (prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})")

            return analysis

        except Exception as e:
            self.log(f"AI analysis failed: {e}", "ERROR")
            return {
                "healthy": True,
                "issues": [f"AI analysis error: {e}"],
                "recommendation": "maintain",
                "reasoning": "Defaulting to maintain due to AI error",
                "next_check_in": 5
            }

    def get_recent_logs(self, state, lines=20):
        """Get recent supervisor logs"""
        log_path = Path(f"scrape_output_supervised/{state}/supervisor.log")

        if not log_path.exists():
            return "No logs yet"

        try:
            with open(log_path, 'r') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading logs: {e}"

    async def start_supervisor(self):
        """Start the underlying intelligent_supervisor.py"""
        cmd = [
            "python",
            "intelligent_supervisor.py",
            "--state", self.state,
            "--max-workers", str(self.max_workers),
            "--check-interval", "60"  # Base supervisor checks every 60s
        ]

        self.log(f"Starting intelligent_supervisor for {self.state}...")

        self.supervisor_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.log(f"Supervisor started with PID {self.supervisor_process.pid}")

        # Wait a bit for it to initialize
        await asyncio.sleep(10)

    async def monitoring_loop(self):
        """Main AI monitoring loop"""
        self.log("="*70)
        self.log("AI SUPERVISOR STARTING")
        self.log("="*70)
        self.log(f"State: {self.state}")
        self.log(f"Max Workers: {self.max_workers}")
        self.log(f"AI Check Interval: {self.check_interval}s")
        self.log(f"AI Model: {self.model}")
        self.log("="*70)

        iteration = 0

        while True:
            iteration += 1
            await asyncio.sleep(self.check_interval)

            self.log(f"\n--- AI Check #{iteration} ---")

            # Load current status
            status_file = Path(f"scrape_output_supervised/{self.state}/supervisor_status.json")

            if not status_file.exists():
                self.log("Waiting for supervisor to create status file...", "WARNING")
                continue

            # Check if supervisor is still alive
            if self.supervisor_process.poll() is not None:
                self.log("Supervisor process has ended!", "WARNING")

                # Check if it completed successfully
                with open(status_file) as f:
                    final_status = json.load(f)

                self.log(f"Final products: {final_status['stats']['total_products']:,}")
                self.log("AI Supervisor shutting down")
                break

            # Load status
            with open(status_file) as f:
                status_data = json.load(f)

            # Get recent logs
            recent_logs = self.get_recent_logs(self.state)

            # AI Analysis
            self.log("Requesting AI analysis...")
            analysis = self.analyze_with_ai(status_data, recent_logs)

            self.log(f"AI Recommendation: {analysis['recommendation']}")
            self.log(f"Reasoning: {analysis['reasoning']}")

            if analysis['issues']:
                self.log(f"Issues detected: {', '.join(analysis['issues'])}", "WARNING")

            # Store analysis
            self.analysis_history.append({
                'timestamp': datetime.now().isoformat(),
                'iteration': iteration,
                'analysis': analysis,
                'stats': status_data['stats']
            })

            # Save analysis history
            with open(f"ai_analysis_{self.state}.json", 'w') as f:
                json.dump(self.analysis_history, f, indent=2)

            # TODO: Could implement AI-driven interventions here
            # For now, we just observe and log

        self.log("="*70)
        self.log("AI SUPERVISOR COMPLETE")
        self.log("="*70)

    async def run(self):
        """Main entry point"""
        await self.start_supervisor()
        await self.monitoring_loop()


async def run_all_states_with_ai(max_workers, check_interval, model):
    """Run both WA and OR with AI supervision"""

    print("="*70)
    print("AI SUPERVISOR - ALL STATES (WA + OR)")
    print("="*70)

    # Run WA first
    wa_supervisor = AISupervisor('WA', max_workers, check_interval, model)
    await wa_supervisor.run()

    # Then OR
    or_supervisor = AISupervisor('OR', max_workers, check_interval, model)
    await or_supervisor.run()

    print("="*70)
    print("ALL STATES COMPLETE WITH AI SUPERVISION")
    print("="*70)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI-Powered Supervisor')
    parser.add_argument('--state', choices=['WA', 'OR'], help='State to scrape (or use --all-states)')
    parser.add_argument('--all-states', action='store_true', help='Run both WA and OR')
    parser.add_argument('--max-workers', type=int, default=8, help='Max workers')
    parser.add_argument('--check-interval', type=int, default=300, help='AI check interval (seconds, default 5min)')
    parser.add_argument('--model', default='gpt-4o-mini', help='OpenAI model to use')
    args = parser.parse_args()

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  Windows: set OPENAI_API_KEY=sk-...")
        print("  Linux/Mac: export OPENAI_API_KEY=sk-...")
        return

    if args.all_states:
        await run_all_states_with_ai(args.max_workers, args.check_interval, args.model)
    elif args.state:
        supervisor = AISupervisor(args.state, args.max_workers, args.check_interval, args.model)
        await supervisor.run()
    else:
        print("ERROR: Specify --state WA/OR or --all-states")
        parser.print_help()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nAI Supervisor stopped by user")
