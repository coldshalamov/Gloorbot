---
name: akamai-resistant-apify-actor
description: Build or refactor lean, low-cost Apify Actors that resist Akamai/WAF blocking using Crawlee/Playwright fingerprints, aligned headers, session + proxy strategy, and cost-optimized parallelism. Use when an actor is blocked, too expensive to run, or needs a cheapest-reliable anti-bot profile.
---

# Akamai Resistant Apify Actor

## Overview

Design the cheapest reliable actor that still passes Akamai-class defenses. Prefer JS/TS with Crawlee fingerprints and session alignment; minimize browsers, keep concurrency modest, and block heavy resources to reduce proxy traffic. This skill is self-contained.

## Workflow Decision Tree

- If Akamai/WAF fingerprinting is present, use JS/TS with Crawlee fingerprints (default on).
- If browser rendering is not required, prefer HTTP scraping with realistic headers and SessionPool.
- If cost is high, pool browsers and cap tabs per browser.
- If block rate rises, reduce concurrency and tighten session/fingerprint alignment.

## Step 1: Confirm Constraints

- No design is 100 percent unblockable; measure block rate and iterate.
- Confirm whether browser rendering is required and which endpoints are allowed.
- Capture volume, schedule, and budget constraints up front.

## Step 2: Choose the Stack

- Prefer JS/TS PlaywrightCrawler with Crawlee fingerprints enabled (default).
- Keep headful mode by default unless target allows headless.
- Avoid manual UA/headers unless you generate them to match the fingerprint.
- Keep dependencies minimal and avoid heavy extras.

## Step 3: Fingerprints and Headers (Cheapest Reliable)

- Keep Crawlee fingerprinting enabled; do not disable useFingerprints.
- Let Crawlee generate realistic headers that align with the fingerprint.
- Only customize UA/headers if generated from the same fingerprint source.
- Keep fingerprints stable within a session and rotate only with the session.
- Do not mix fingerprints across parallel contexts on the same proxy session.

## Step 4: Session + Proxy Strategy

- Use SessionPool with maxUsageCount and maxErrorScore to rotate sessions on blocks.
- Residential sessions are short-lived unless kept active; keep traffic flowing if you need continuity.
- One proxy session per browser context; one fingerprint per session.
- Rotate fingerprint only when the session rotates.

## Step 5: Parallelism and Cost Control

- Pool browsers: one browser per store or proxy session.
- Reuse the browser across all pages for that unit.
- Create a small number of concurrent pages per browser (2-4).
- Block images, media, and fonts when possible to reduce proxy bandwidth.
- Avoid screenshots unless debugging.

## Step 6: Blocking Detection and Recovery

- Detect “Access Denied” pages, challenge pages, or unexpected redirects.
- Treat timeouts, empty results, and crash pages as block signals.
- Retry with exponential backoff; rotate session + fingerprint on repeated errors.
- Reduce concurrency when block rate increases.

## Step 7: Verification Playbook

- Log per-session fingerprint metadata (UA, locale, timezone, viewport) and proxy session id.
- Confirm no shared fingerprint across different proxy sessions.
- Track block rate per 100 requests; if it rises, reduce concurrency or rotate sooner.
- Track compute hours and proxy bandwidth to verify cost wins.

## Minimal Output Contract (example)

Push to dataset items with:
- store_id, store_name, zip
- sku, title, category
- product_url, image_url
- price, price_was, pct_off
- availability, clearance, timestamp
