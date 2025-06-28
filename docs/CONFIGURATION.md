# PhishFish Configuration Guide

This guide explains all of the different configuration options available in your `.env` file.

## Configuration Variables

### Logging Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | ❌ | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL` |

---

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

### Email Connection & Authentication Settings

Configure your email server connection and authentication method.

#### Basic IMAP Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IMAP_HOST` | ⚠️ | *None* | Your email server hostname |
| `IMAP_USER` | ⚠️ | *None* | Your email username/address |
| `IMAP_PORT` | ❌ | `993` | IMAP server port (usually 993 for SSL) |
| `IMAP_ENCRYPTION_METHOD` | ❌ | `SSL` | Encryption method: `SSL`, `TLS`, `STARTTLS`, or `NONE` |
| `MAILBOX` | ❌ | `INBOX` | Mailbox folder to monitor for new emails |

#### Authentication Methods

**Option 1: OAuth 2.0**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_OAUTH` | ❌ | `false` | Enable OAuth 2.0 authentication instead of password |
| `OAUTH_CLIENT_ID` | ⚠️* | *None* | OAuth 2.0 client ID from your provider |
| `OAUTH_CLIENT_SECRET` | ⚠️* | *None* | OAuth 2.0 client secret from your provider |
| `OAUTH_AUTH_URL` | ⚠️* | *None* | OAuth authorization endpoint URL |
| `OAUTH_TOKEN_URL` | ⚠️* | *None* | OAuth token endpoint URL |
| `OAUTH_SCOPE` | ⚠️* | *None* | OAuth scopes (comma-separated) |
| `OAUTH_CALLBACK_PORT` | ❌ | `8080` | Port for OAuth callback server during authentication |

*Required when `USE_OAUTH=true`

> **Note**: When using OAuth, ensure the Docker port mapping matches your `OAUTH_CALLBACK_PORT` setting. For example, if you set `OAUTH_CALLBACK_PORT=9090`, use `-p 9090:9090` in your Docker run command.

**Option 2: Password/App Password**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IMAP_PASS` | ⚠️** | *None* | Your email password or app password |

**Required when `USE_OAUTH=false`

---

### Notification Settings

PhishFish can send notifications via [ntfy.sh](https://ntfy.sh) when phishing emails are detected. A notification will only be sent if `NTFY_TOPIC` is set.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NTFY_TOPIC` | ❌ | *None* | Your unique ntfy topic name |
| `NTFY_URL` | ❌ | `https://ntfy.sh` | Custom ntfy server URL (no trailing slash) |
| `NTFY_TITLE` | ❌ | `PhishFish Email Report` | Title for ntfy notifications
| `NOTIFY_ON` | ❌ | `phishing` | Which classifications to notify about |

#### Setting Up Notifications

1. **Choose a unique topic name**
2. **Install the ntfy app** on your phone:
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

---

### Moving Email Settings

PhishFish can move detected phishing emails to a specified folder if you wish. 

Folders often have different names on the server to what you may be expecting. All available folders are displayed in the log when you start up PhishFish.

Emails will only be moved if `MOVE_TO_FOLDER` is set.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MOVE_TO_FOLDER` | ❌ | *None* | The folder to move detected phishing emails to. |
