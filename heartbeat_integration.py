"""
Gloorbot Heartbeat Integration

Add this to your Gloorbot scraper to send heartbeat signals to CheapSkater admin dashboard.

INSTALLATION:
1. Copy this file to your Gloorbot directory
2. Import and call send_heartbeat() periodically from your main scraper loop
3. Set CHEAPSKATER_API_URL and CHEAPSKATER_API_KEY environment variables

USAGE:
    from heartbeat_integration import send_heartbeat

    # In your main scraper loop, call periodically:
    send_heartbeat(
        client_id="gloorbot-main",
        deals_count=batch_size,
        errors_count=errors
    )
"""

import os
import socket
import requests
from datetime import datetime


# Configuration
CHEAPSKATER_API_URL = os.getenv(
    "CHEAPSKATER_API_URL",
    "https://cheapskater.onrender.com"  # Default to production
)
CHEAPSKATER_API_KEY = os.getenv("CHEAPSKATER_INGEST_API_KEY", "")
HEARTBEAT_ENDPOINT = f"{CHEAPSKATER_API_URL}/admin/api/heartbeat"

# Scraper version (update this as you release new versions)
SCRAPER_VERSION = "1.0.0"


def get_hostname():
    """Get the hostname of the machine running the scraper."""
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def send_heartbeat(
    client_id: str,
    deals_count: int = 0,
    errors_count: int = 0,
    status_message: str | None = None,
    scraper_name: str | None = None,
):
    """
    Send heartbeat to CheapSkater admin dashboard.

    Args:
        client_id: Unique identifier for this scraper instance
        deals_count: Number of deals processed since last heartbeat
        errors_count: Number of errors encountered since last heartbeat
        status_message: Optional status message
        scraper_name: Optional human-readable scraper name

    Returns:
        True if heartbeat was successful, False otherwise
    """
    if not CHEAPSKATER_API_KEY:
        print("[HEARTBEAT] Warning: CHEAPSKATER_INGEST_API_KEY not set, skipping heartbeat")
        return False

    payload = {
        "scraper_id": client_id,
        "scraper_name": scraper_name or f"Gloorbot-{client_id}",
        "deals_count": deals_count,
        "errors_count": errors_count,
        "status_message": status_message or f"Running - {deals_count} deals processed",
        "version": SCRAPER_VERSION,
        "hostname": get_hostname(),
    }

    headers = {
        "X-API-Key": CHEAPSKATER_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            HEARTBEAT_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            print(f"[HEARTBEAT] ✓ Sent heartbeat for {client_id}")
            return True
        else:
            print(f"[HEARTBEAT] ✗ Failed: HTTP {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("[HEARTBEAT] ✗ Timeout")
        return False
    except Exception as e:
        print(f"[HEARTBEAT] ✗ Error: {e}")
        return False


# Example usage
if __name__ == "__main__":
    # Test the heartbeat
    success = send_heartbeat(
        client_id="gloorbot-test",
        deals_count=100,
        errors_count=5,
        status_message="Test heartbeat from standalone script"
    )

    if success:
        print("Heartbeat test successful!")
    else:
        print("Heartbeat test failed. Check your configuration.")
