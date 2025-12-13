# AWS Deployment Guide - Lowe's Scraper

## Cost: ~$30/crawl (vs $70-80 on Apify)

---

## Architecture

```
AWS EC2 Spot Instance (c6i.2xlarge)
  ↓
Docker Container (Playwright + Python)
  ↓
Bright Data Residential Proxies
  ↓
Results → S3 Bucket or PostgreSQL RDS
```

---

## Setup Steps

### 1. Create AWS Account & Install CLI

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

### 2. Create S3 Bucket for Results

```bash
aws s3 mb s3://lowes-scraper-results
```

### 3. Create Spot Instance Launch Template

```bash
# Create launch template
aws ec2 create-launch-template \
  --launch-template-name lowes-scraper \
  --version-description "Optimized Lowe's scraper" \
  --launch-template-data '{
    "ImageId": "ami-0c55b159cbfafe1f0",
    "InstanceType": "c6i.2xlarge",
    "KeyName": "your-key-pair",
    "IamInstanceProfile": {
      "Name": "EC2-S3-Access"
    },
    "UserData": "BASE64_ENCODED_STARTUP_SCRIPT"
  }'
```

### 4. Request Spot Instance

```bash
# Request spot instance (70% cheaper!)
aws ec2 request-spot-instances \
  --spot-price "0.15" \
  --instance-count 1 \
  --type "one-time" \
  --launch-specification '{
    "ImageId": "ami-0c55b159cbfafe1f0",
    "InstanceType": "c6i.2xlarge",
    "KeyName": "your-key-pair"
  }'
```

---

## Docker Setup

### Dockerfile

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy scraper code
COPY src/ ./src/
COPY input/ ./input/
COPY catalog/ ./catalog/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV BRIGHT_DATA_USERNAME=your_username
ENV BRIGHT_DATA_PASSWORD=your_password

# Run scraper
CMD ["python", "src/main_optimized.py"]
```

### Build & Push to ECR

```bash
# Create ECR repository
aws ecr create-repository --repository-name lowes-scraper

# Build image
docker build -t lowes-scraper .

# Tag for ECR
docker tag lowes-scraper:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/lowes-scraper:latest

# Push to ECR
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/lowes-scraper:latest
```

---

## Bright Data Proxy Configuration

### Sign up for Bright Data
1. Go to https://brightdata.com
2. Create account
3. Create "Residential Proxy" zone
4. Get credentials

### Modify Scraper for Bright Data

```python
# In main_optimized.py, replace proxy configuration:

# OLD (Apify):
proxy_config = await Actor.create_proxy_configuration(
    groups=["RESIDENTIAL"],
    country_code="US",
)

# NEW (Bright Data):
BRIGHT_DATA_HOST = "brd.superproxy.io"
BRIGHT_DATA_PORT = 22225
BRIGHT_DATA_USERNAME = os.getenv("BRIGHT_DATA_USERNAME")
BRIGHT_DATA_PASSWORD = os.getenv("BRIGHT_DATA_PASSWORD")

def get_proxy_url(session_id: str) -> str:
    """Generate Bright Data proxy URL with session locking."""
    username = f"{BRIGHT_DATA_USERNAME}-session-{session_id}"
    return f"http://{username}:{BRIGHT_DATA_PASSWORD}@{BRIGHT_DATA_HOST}:{BRIGHT_DATA_PORT}"

# In browser launch:
proxy_url = get_proxy_url(f"store_{store_id}")
launch_options["proxy"] = {"server": proxy_url}
```

---

## Automated Deployment Script

```bash
#!/bin/bash
# deploy_scraper.sh

set -e

echo "🚀 Deploying Lowe's Scraper to AWS..."

# 1. Request spot instance
INSTANCE_ID=$(aws ec2 request-spot-instances \
  --spot-price "0.15" \
  --instance-count 1 \
  --type "one-time" \
  --launch-specification file://spot-config.json \
  --query 'SpotInstanceRequests[0].InstanceId' \
  --output text)

echo "✅ Spot instance requested: $INSTANCE_ID"

# 2. Wait for instance to be running
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# 3. Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "✅ Instance running at: $INSTANCE_IP"

# 4. SSH and run scraper
ssh -i ~/.ssh/your-key.pem ec2-user@$INSTANCE_IP << 'EOF'
  # Pull latest code
  git clone https://github.com/your-repo/Gloorbot.git
  cd Gloorbot/apify_actor_seed
  
  # Install dependencies
  pip install -r requirements.txt
  playwright install chromium
  
  # Run scraper
  python src/main_optimized.py
  
  # Upload results to S3
  aws s3 cp results.json s3://lowes-scraper-results/$(date +%Y%m%d_%H%M%S).json
EOF

echo "✅ Scraper complete! Results uploaded to S3"

# 5. Terminate instance (save money!)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID

echo "✅ Instance terminated. Total cost: ~$0.12 compute + $30 proxies = $30.12"
```

---

## Cost Optimization Tips

### 1. Use Spot Instances (70% savings)
```bash
# Regular: $0.34/hr
# Spot: $0.10/hr
# Savings: $0.24/hr
```

### 2. Terminate Immediately After Scrape
```bash
# Don't leave instance running!
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

### 3. Use S3 Lifecycle Policies
```bash
# Delete old results after 30 days
aws s3api put-bucket-lifecycle-configuration \
  --bucket lowes-scraper-results \
  --lifecycle-configuration file://lifecycle.json
```

### 4. Optimize Proxy Usage
```python
# Only use proxies for Lowe's requests
# Use direct connection for S3 uploads
```

---

## Alternative: Lambda + Step Functions

For even cheaper (but more complex):

```
AWS Lambda (15-minute max)
  ↓
Step Functions (orchestrate multiple Lambdas)
  ↓
Each Lambda handles 1 store
  ↓
Results → DynamoDB or S3
```

**Cost:**
- Lambda: $0.0000166667/GB-second
- 50 concurrent Lambdas × 3GB × 900 seconds = 135,000 GB-seconds
- **$2.25/crawl** + $30 proxies = **$32.25/crawl**

---

## Monitoring & Alerts

```bash
# CloudWatch alarm for cost overruns
aws cloudwatch put-metric-alarm \
  --alarm-name lowes-scraper-cost-alert \
  --alarm-description "Alert if scraper costs exceed $50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold
```

---

## Summary

| Platform | Cost/Crawl | Setup Complexity | Control |
|----------|-----------|------------------|---------|
| **Apify** | $70-80 | ⭐ Easy | ⭐⭐ Limited |
| **AWS EC2 Spot** | $30 | ⭐⭐ Medium | ⭐⭐⭐⭐⭐ Full |
| **GCP Cloud Run** | $26 | ⭐⭐ Medium | ⭐⭐⭐⭐ Good |
| **Hetzner** | $10-15 | ⭐⭐⭐ Complex | ⭐⭐⭐⭐⭐ Full |
| **AWS Lambda** | $32 | ⭐⭐⭐⭐ Hard | ⭐⭐⭐ Good |

**Recommendation:** Start with AWS EC2 Spot for best cost/complexity balance.
