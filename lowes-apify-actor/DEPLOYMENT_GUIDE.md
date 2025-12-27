# Lowe's Apify Actor Deployment Guide

This is the **ultra-optimized, smart version** of the Lowe's Inventory Scraper. It is designed to bypass Akamai blocking while maintaining low operational costs on the Apify platform.

## 🚀 Key Features
- **Full Coverage & Persistence**: Scrapes all 49 WA/OR stores and ~200+ categories from `LowesMap.txt`.
- **Clean Restarts**: Progress is saved to Apify Key-Value Store (`SCRAPER_STATE`). If the actor restarts or migrates, it resumes exactly where it left off.
- **Akamai Evasion**: Advanced fingerprint randomization (Canvas, WebGL, AudioContext, Screen).
- **Cost Optimized**: 
  - **Bandwidth**: Blocks images, fonts, and media by default (60-70% savings).
  - **Memory**: Runs 3 stores in parallel per browser context to stay within 4GB.
- **Infinite Pagination**: Scrapes every single product listing in every category.


## 📂 Consolidated File Structure
- `src/main.py`: The "Smart" actor logic.
- `src/proxy_config.py`: Configuration for external proxy providers.
- `.actor/`: Apify actor metadata and input schema.
- `app/retailers/lowes.py`: Helper logic for store selection.
- `Dockerfile`: Configured for Python Playwright (Headless=False).
- `requirements.txt`: Minimal dependencies.

## ⚙️ Recommended Apify Settings
- **Memory**: **4096 MB** (4GB). Do not go lower, as Playwright needs it.
- **Proxies**: Use **Residential Proxies**. 
  - Apify Proxies: Select "Residential" and set country to "US".
  - External Proxies: If using Proxy-Cheap or similar, set the environment variables listed below.

## 🛠️ Environment Variables (Optional)
| Variable | Default | Description |
|----------|---------|-------------|
| `CHEAPSKATER_PICKUP_FILTER` | `1` | Enable/Disable "Pickup Today" filtering. |
| `CHEAPSKATER_BLOCK_RESOURCES` | `1` | Enable/Disable image/font blocking (Cost savings). |
| `CHEAPSKATER_RANDOM_UA` | `0` | Enable rotating User Agents. |
| `PROXY_PROVIDER` | `none` | Use external provider (e.g., `proxy-cheap`, `smartproxy`). |
| `PROXYCHEAP_USERNAME` / `PASSWORD` | - | Credentials if using Proxy-Cheap. |

## 📦 How to Deploy
1. Zip the contents of this folder.
2. Go to [Apify Console](https://console.apify.com/actors).
3. Create a new Actor from Source Code.
4. Upload the zip file or push via Apify CLI.
5. Set the **Build tag** to `latest`.
6. Use the **4096 MB** memory setting for the run.

---
*Created by Antigravity AI for optimized Lowe's markdown hunting.*
