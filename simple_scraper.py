"""
Simple launcher for the PARALLEL scraper.
This is what gets packaged as the distributable exe.
"""
import os
import sys
from pathlib import Path

def main():
    # Find PARALLEL folder - either bundled with exe or in repo
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller exe
        base = Path(sys._MEIPASS)
    else:
        # Running as script
        base = Path(__file__).parent
    
    parallel_dir = base / "PARALLEL"
    if not parallel_dir.exists():
        parallel_dir = base.parent / "PARALLEL"
    
    if not parallel_dir.exists():
        print("ERROR: Could not find PARALLEL folder!")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Change to PARALLEL directory so relative paths work
    os.chdir(parallel_dir)
    
    # Add to path so imports work
    sys.path.insert(0, str(parallel_dir))
    
    print("=" * 60)
    print("Lowe's Deal Scraper")
    print("=" * 60)
    print()
    print("This will scrape all WA and OR Lowe's stores for deals.")
    print("It runs 5 browser windows in parallel.")
    print()
    print("Output will be saved to: PARALLEL/output/")
    print("Progress is saved, so you can stop and resume anytime.")
    print()
    input("Press Enter to start...")
    print()
    
    # Import and run the orchestrator
    import orchestrator
    import asyncio
    
    # Create orchestrator with default settings matching start.bat
    orch = orchestrator.IntelligentOrchestrator(
        state="WA,OR",
        max_workers=5,
        use_ai=False,
        openai_api_key=None,
        research_mode=False
    )
    
    # Run it
    asyncio.run(orch.run())
    
    print()
    print("Done! Check PARALLEL/output/ for results.")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
