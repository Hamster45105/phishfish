# PhishFish Configuration Guide

This guide explains all of the different configuration options available in your `.env` file.

## Configuration Variables

### Azure AI Configuration

PhishFish uses Azure AI (via GitHub Models) to classify emails as legitimate or phishing.

GitHub models is free for all users, but with [rate limits](https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models#rate-limits)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | ⚠️ | *None* | Your GitHub personal access token with model access |
| `AZURE_MODEL` | ❌ | `openai/gpt-4.1` | AI model to use for email classification |
| `AZURE_ENDPOINT` | ❌ | `https://models.github.ai/inference` | Azure AI inference endpoint |

#### Getting a GitHub Token
1. Go to [GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token](https://github.com/settings/personal-access-tokens/new)
2. Generate a new token with `Models` access
3. Copy the token to your `.env` file

---

### IMAP Email Settings

Configure your email server connection to monitor for new emails.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IMAP_HOST` | ⚠️ | *None* | Your email server hostname |
| `IMAP_USER` | ⚠️ | *None* | Your email username/address |
| `IMAP_PASS` | ⚠️ | *None* | Your email password or app password |
| `IMAP_PORT` | ❌ | `993` | IMAP server port (usually 993 for SSL) |
| `IMAP_AUTH_METHOD` | ❌ | `SSL` | Authentication method: `SSL`, `STARTTLS`, or `PLAIN` |
| `MAILBOX` | ❌ | `INBOX` | Mailbox folder to monitor for new emails |

#### Known Email Settings

<details>
<summary><strong>Gmail</strong></summary>

#### Config

```bash
IMAP_HOST=imap.gmail.com
IMAP_USER=your-email@gmail.com
IMAP_PASS=your-app-password
IMAP_PORT=993
IMAP_AUTH_METHOD=SSL
MAILBOX=INBOX
```

#### Tips

- Enable 2-factor authentication
- Generate an App Password (not your regular password)
</details>

---

### Notification Settings

PhishFish can send notifications via [ntfy.sh](https://ntfy.sh) when phishing emails are detected.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NTFY_TOPIC` | ❌ | *None* | Your unique ntfy.sh topic name |
| `NTFY_URL` | ❌ | `https://ntfy.sh/{TOPIC}` | Custom ntfy server URL (no trailing slash) |
| `NTFY_TITLE` | ❌ | `PhishFish Email Report` | Title for NTFY notifications
| `NOTIFY_ON` | ❌ | `phishing` | Which classifications to notify about |

#### Setting Up Notifications

1. **Choose a unique topic name** (e.g., `john-phishing-alerts-2024`)
2. **Install ntfy app** on your phone:
   - [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - [iOS](https://apps.apple.com/us/app/ntfy/id1625396347)
3. **Subscribe to your topic** in the app
4. **Test it** by visiting `https://ntfy.sh/your-topic-name` and sending a test message

#### Notification Filtering

Use `NOTIFY_ON` to control which email classifications trigger notifications:

```bash
# Notify only on phishing (default)
NOTIFY_ON=phishing

# Notify on both phishing and legitimate emails
NOTIFY_ON=phishing,legitimate

```
### Moving Email Settings

PhishFish can move detected phishing emails to a specified folder if you wish.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MOVE_TO_FOLDER` | ❌ | *None* | The folder to move detected phishing emails to. All available folders are displayed in the logs when run |
