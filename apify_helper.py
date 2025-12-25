#!/usr/bin/env python3
"""
Apify Helper Script
Usage: python apify_helper.py [command] [args]

Commands:
    list                    - List all actors
    run <actor> <input>    - Run an actor with JSON input
    status <run_id>        - Check run status
    results <run_id>       - Get run results

Examples:
    python apify_helper.py list
    python apify_helper.py run lowes-cheapskate '{"stores":[{"store_id":"0004"}]}'
    python apify_helper.py status abc123
"""

import os
import sys
import json
import time
import requests

# API credentials
API_TOKEN = os.getenv('APIFY_TOKEN', 'apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM')
BASE_URL = 'https://api.apify.com/v2'
HEADERS = {'Authorization': f'Bearer {API_TOKEN}'}

def list_actors():
    """List all actors"""
    response = requests.get(f'{BASE_URL}/acts', headers=HEADERS)
    response.raise_for_status()
    actors = response.json()['data']['items']

    print(f"\n{'='*60}")
    print(f"Found {len(actors)} actors:")
    print(f"{'='*60}\n")

    for actor in actors:
        print(f"  • {actor['name']}")
        print(f"    ID: {actor['id']}")
        print(f"    Runs: {actor['stats']['totalRuns']}")
        print()

def run_actor(actor_name, input_data):
    """Run an actor with input"""
    if isinstance(input_data, str):
        input_data = json.loads(input_data)

    url = f"{BASE_URL}/acts/one-api~{actor_name}/runs"
    response = requests.post(url, headers=HEADERS, json=input_data)
    response.raise_for_status()

    run_data = response.json()['data']
    run_id = run_data['id']

    print(f"\n✓ Actor '{actor_name}' started successfully!")
    print(f"  Run ID: {run_id}")
    print(f"  Status: {run_data['status']}")
    print(f"\nMonitoring progress...\n")

    # Monitor until completion
    while True:
        status_response = requests.get(
            f"{BASE_URL}/actor-runs/{run_id}",
            headers=HEADERS
        )
        status_data = status_response.json()['data']
        status = status_data['status']

        print(f"  [{time.strftime('%H:%M:%S')}] Status: {status}")

        if status == 'SUCCEEDED':
            print(f"\n✓ Actor completed successfully!")
            dataset_id = status_data['defaultDatasetId']

            # Download results
            results_response = requests.get(
                f"{BASE_URL}/datasets/{dataset_id}/items?format=json",
                headers=HEADERS
            )
            results = results_response.json()

            filename = f'results_{run_id}.json'
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)

            print(f"  Downloaded {len(results)} items to {filename}")
            return run_id

        elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
            print(f"\n✗ Actor failed with status: {status}")
            print(f"\nError details:")
            print(json.dumps(status_data, indent=2))
            sys.exit(1)

        time.sleep(10)

def get_status(run_id):
    """Get run status"""
    response = requests.get(f'{BASE_URL}/actor-runs/{run_id}', headers=HEADERS)
    response.raise_for_status()
    data = response.json()['data']

    print(f"\nRun ID: {run_id}")
    print(f"Status: {data['status']}")
    print(f"Started: {data['startedAt']}")

    if data.get('finishedAt'):
        print(f"Finished: {data['finishedAt']}")

    if data['status'] == 'SUCCEEDED':
        print(f"Dataset ID: {data['defaultDatasetId']}")

def get_results(run_id):
    """Get run results"""
    # First get the run to find dataset
    response = requests.get(f'{BASE_URL}/actor-runs/{run_id}', headers=HEADERS)
    response.raise_for_status()
    dataset_id = response.json()['data']['defaultDatasetId']

    # Get dataset items
    results_response = requests.get(
        f'{BASE_URL}/datasets/{dataset_id}/items?format=json',
        headers=HEADERS
    )
    results_response.raise_for_status()
    results = results_response.json()

    filename = f'results_{run_id}.json'
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Downloaded {len(results)} items to {filename}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == 'list':
            list_actors()

        elif command == 'run':
            if len(sys.argv) < 3:
                print("Error: Actor name required")
                print("Usage: python apify_helper.py run <actor_name> <input_json>")
                sys.exit(1)

            actor = sys.argv[2]
            input_data = sys.argv[3] if len(sys.argv) > 3 else '{}'
            run_actor(actor, input_data)

        elif command == 'status':
            if len(sys.argv) < 3:
                print("Error: Run ID required")
                sys.exit(1)
            get_status(sys.argv[2])

        elif command == 'results':
            if len(sys.argv) < 3:
                print("Error: Run ID required")
                sys.exit(1)
            get_results(sys.argv[2])

        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ API Error: {e}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
