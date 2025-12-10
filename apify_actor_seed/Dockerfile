# Headful Playwright-ready image with Xvfb for Akamai bypass
FROM apify/actor-python-playwright:3.12

# Copy all files
COPY . ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables for headful mode
ENV DISPLAY=:99
ENV CHEAPSKATER_HEADLESS=false

# Run the main Actor
CMD ["python", "-m", "src.main"]
