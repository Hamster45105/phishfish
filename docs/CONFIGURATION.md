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

### Sender Lists

Sometimes, you may not want PhishFish sending your emails to the AI for classification. This may be for privacy reasones* or because you know certain domains are safe or dangerous. 

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DANGEROUS_SENDERS` | ❌ | *None* | Comma-separated list of dangerous senders (auto-classified as phishing) |
| `SAFE_SENDERS` | ❌ | *None* | Comma-separated list of safe senders (auto-classified as legitimate) |

#### Configuring Sender Lists

You can combine both email addresses and domains:
```bash
DANGEROUS_SENDERS=scammer@fake-bank.com,@scam-domain.com
SAFE_SENDERS=boss@company.com,@localshop.com
```

#### Conflict Resolution

If a sender appears in both dangerous and safe lists, PhishFish uses the following rules:

1. **Exact Same Entry**: If the exact same entry (email or domain) appears in both lists, **dangerous takes precedence**
   ```bash
   DANGEROUS_SENDERS=example@company.com,@suspicious.com
   SAFE_SENDERS=example@company.com,@trusted.com
   # Result: example@company.com → dangerous (with warning logged)
   ```

2. **Different Match Types**: If there's a conflict between email and domain matches, **specific email takes precedence** over domain
   ```bash
   DANGEROUS_SENDERS=@company.com
   SAFE_SENDERS=admin@company.com
   # Result: admin@company.com → safe (specific email overrides domain)
   
   DANGEROUS_SENDERS=admin@company.com
   SAFE_SENDERS=@company.com
   # Result: admin@company.com → dangerous (specific email overrides domain)
   ```

All conflicts are logged with warnings explaining which rule was applied.

> **Note**: Sender lists are checked before AI classification. If a sender is found in either list, the email is instantly classified without using AI, saving processing time and API calls.

\* Realistically, if you use an commercial email service, your emails are probably getting read by an AI anyway.

---

### Moving Email Settings

PhishFish can move detected phishing emails to a specified folder if you wish. 

Folders often have different names on the server to what you may be expecting. All available folders are displayed in the log when you start up PhishFish.

Emails will only be moved if `MOVE_TO_FOLDER` is set.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MOVE_TO_FOLDER` | ❌ | *None* | The folder to move detected phishing emails to. |
