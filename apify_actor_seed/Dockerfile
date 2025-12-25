# Python Playwright image needed for the Python-based actor
FROM apify/actor-python-playwright:3.11

# Copy all files
COPY . ./

# Install dependencies
RUN pip install -r requirements.txt

# Run the Python Actor (this has the AKAMAI fixes)
CMD ["python", "src/main.py"]
