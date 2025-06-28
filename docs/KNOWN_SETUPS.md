# Known Email Provider Configurations

This guide provides step-by-step configuration examples for popular email providers. 

## Index

| Provider | Setup Guide |
|----------|-------------|
| <img src="https://cdn.jsdelivr.net/npm/simple-icons@v15/icons/gmail.svg" width="20" height="20"> Gmail | [Configuration →](#gmail) |
| <img src="https://cdn.jsdelivr.net/npm/simple-icons@v15/icons/microsoftoutlook.svg" width="20" height="20"> Outlook/Microsoft | [Configuration →](#outlook--microsoft) |

---

## Gmail

Gmail supports both app passwords and OAuth 2.0. App passwords are simpler to set up.

**Prerequisites:**
- [Enable 2-factor authentication](https://support.google.com/accounts/answer/185839) on your Google account
- [Generate an app password](https://myaccount.google.com/apppasswords) specifically for PhishFish

**Configuration:**
```bash
# IMAP Settings
IMAP_HOST=imap.gmail.com
IMAP_USER=your-email@gmail.com
IMAP_PASS=your-16-character-app-password
IMAP_PORT=993
IMAP_ENCRYPTION_METHOD=SSL
MAILBOX=INBOX
```

---

## Outlook / Microsoft

Microsoft requires OAuth 2.0 for modern authentication.

**Prerequisites:**
- [Register an application](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) in Azure AD
- Add redirect URI: `http://localhost:8080/callback` (replace `8080` with a custom port, if applicable)
- Grant `IMAP.AccessAsUser.All` and `offline_access` permissions

**Configuration:**
```bash
# IMAP Settings
IMAP_HOST=outlook.office365.com
IMAP_USER=your-email@outlook.com
IMAP_PORT=993
IMAP_ENCRYPTION_METHOD=SSL
MAILBOX=INBOX

# OAuth Settings
USE_OAUTH=true
OAUTH_CLIENT_ID=your-application-id
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_AUTH_URL=https://login.microsoftonline.com/common/oauth2/v2.0/authorize
OAUTH_TOKEN_URL=https://login.microsoftonline.com/common/oauth2/v2.0/token
OAUTH_SCOPE=https://outlook.office.com/IMAP.AccessAsUser.All,offline_access
OAUTH_CALLBACK_PORT=8080
```