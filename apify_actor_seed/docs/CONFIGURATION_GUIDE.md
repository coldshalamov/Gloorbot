# Apify Actor Configuration Guide

This file contains the templates Claude needs to create the **Actor metadata** (`actor.json`) and **Container** (`Dockerfile`).

## 1. `Dockerfile`
**Instruction**: Create a `.actor/Dockerfile` using the following template. It uses the `actor-python-playwright` base image which includes Xvfb (essential for `headless=False`).

```dockerfile
# Use the official Apify Python Playwright image (includes Xvfb)
# See: https://hub.docker.com/r/apify/actor-python-playwright
FROM apify/actor-python-playwright:3.12

# Copy requirements FIRST to leverage Docker cache
COPY requirements.txt ./

# Install dependencies (playwright-stealth, etc)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY . .

# Launch the Actor
# Important: Xvfb is handled automatically by the base image's entrypoint
CMD ["python", "-m", "src.main"]
```

## 2. `actor.json`
**Instruction**: Create a `.actor/actor.json` file. This defines the Actor's interface on the Apify platform.

```json
{
    "actorSpecification": 1,
    "name": "lowes-scraper-pro",
    "version": "1.0",
    "buildTag": "latest",
    "minMemoryMbytes": 1024,
    "maxMemoryMbytes": 4096,
    "dockerfile": "./.actor/Dockerfile",
    "input": "./.actor/input_schema.json",
    "storages": {
        "dataset": "./.actor/dataset_schema.json"
    }
}
```

## 3. `input_schema.json`
**Instruction**: Create a `.actor/input_schema.json` to define the inputs.

```json
{
    "title": "Lowes Scraper Input",
    "type": "object",
    "schemaVersion": 1,
    "properties": {
        "store_ids": {
            "title": "Store IDs",
            "type": "array",
            "description": "List of Lowe's Store IDs to scrape.",
            "editor": "stringList",
            "default": []
        },
        "zip_codes": {
             "title": "Zip Codes",
             "type": "array",
             "description": "List of Zip Codes to auto-discover stores from.",
             "editor": "stringList",
             "default": []
        },
        "categories": {
            "title": "Categories",
            "type": "array",
            "description": "Specific categories to scrape (e.g. 'building-materials').",
            "editor": "stringList",
            "default": []
        },
        "use_stealth": {
            "title": "Use Stealth",
            "type": "boolean",
            "description": "Enable playwright-stealth.",
            "default": true
        },
        "max_items": {
            "title": "Max Items",
            "type": "integer",
            "description": "Maximum items to scrape per store.",
            "default": 1000
        }
    }
}
```
