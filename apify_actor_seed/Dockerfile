# Headful Playwright-ready image with Xvfb for Akamai bypass
FROM apify/actor-node-playwright:18

# Copy all files
COPY . ./

# Install dependencies
RUN npm install --omit=dev

# Set environment variables for headful mode
ENV APIFY_XVFB=1

# Run the main Actor
CMD ["node", "src/main.js"]
