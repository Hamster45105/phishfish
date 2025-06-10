# 🐟 PhishFish

<p align="center">
  <img src=".github/banner.png" alt="PhishFish Icon" height="80" style="float:left; margin-right: 20px;">
</p>

**Self-hosted AI-powered email phishing protection**

PhishFish monitors your email in real-time and uses free access to the GitHub models API to utilise LLMs and detect phishing attempts, and send notifcations to ntfy.sh when a phishing email is found. 

## 🚀 Quick Start with Docker

### Prerequisites
- Docker installed
- Email account with IMAP access
- GitHub token for AI models
- ntfy.sh topic for notifications

### Setup and Run
```bash
# 1. Create project directory
mkdir phishfish && cd phishfish

# 2. Download configuration template
curl -o .env.example https://raw.githubusercontent.com/Hamster45105/phishfish/main/.env.example

# 3. Configure your settings
cp .env.example .env
nano .env  # Edit with your settings

# 4. Create logs directory and run
mkdir logs
docker run -d \
  --name phishfish \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  ghcr.io/Hamster45105/phishfish:latest
```

### View Logs
```bash
# Follow container logs
docker logs -f phishfish

# Or view log file directly
tail -f logs/$(date +%Y-%m-%d).log
```

## Example Notification
```
PhishFish Email Report

SENDER: "security@amaz0n.com"

SUBJECT: "Urgent: Verify Your Account"

CLASSIFICATION: 🔴 phishing

REASON: Suspicious sender domain and urgent language typical of phishing attempts.

ADVICE: Ignore the email, delete it, or do not click any links.
```

## ⚙️ Configuration

See [CONFIGURATION.md](docs/CONFIGURATION.md) for detailed setup instructions.
