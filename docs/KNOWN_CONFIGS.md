# Known Email Provider Configurations

This guide provides step-by-step configuration examples for popular email providers. 

## Authentication Methods

PhishFish supports *two* authentication methods - **basic** (username and password) and **OAuth 2.0**. OAuth 2.0 is more modern and consdidered more secure, but is more difficult to set up for PhishFish. For that reason, it is recommended you use basic authentication where possible. 

For services that provide both options, only a guide on basic authentication will be provided.

Currently, the OAuth 2.0 integration is experimental in PhishFish, so use at your own risk.

## Index

| Provider | Setup Guide |
|----------|-------------|
| Gmail <img src="https://cdn.simpleicons.org/gmail/EA4335" alt="Gmail" align=left width=19 height=19> | [Configuration →](#gmail) |
| iCloud <img src="https://cdn.simpleicons.org/icloud/3693F3" alt="iCloud" align=left width=19 height=19> | [Configuration →](#icloud) |
| Outlook/Microsoft | [Configuration →](#outlook--microsoft) |

---

## Gmail

Gmail supports both basic and OAuth 2.0 authentication.

**Prerequisites:**
- [Enable 2-factor authentication](https://support.google.com/accounts/answer/185839) on your Google account
- [Generate an app password](https://myaccount.google.com/apppasswords) specifically for PhishFish

**Configuration:**
```bash
# IMAP Settings
IMAP_HOST=imap.gmail.com
IMAP_USER=your-email@gmail.com
IMAP_PASS=your-app-password
IMAP_PORT=993
IMAP_ENCRYPTION_METHOD=SSL
```

---

## iCloud

iCloud Mail requires basic authentication.

**Prerequisites:**
- [Generate an app-specific password](https://support.apple.com/kb/HT204397) for PhishFish

**Configuration:**
```bash
# IMAP Settings
IMAP_HOST=imap.mail.me.com
IMAP_USER=your-email@icloud.com
IMAP_PASS=your-app-specific-password
IMAP_PORT=993
IMAP_ENCRYPTION_METHOD=SSL
```

**Notes:**
- You username is usually the name of your iCloud Mail email address (for example, johnappleseed, not johnappleseed@icloud.com). If this does not work, try using the full address.
- The app-specific password is different from your regular Apple ID password

---

## Outlook / Microsoft

Microsoft requires OAuth 2.0 authentication.

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

# OAuth Settings
USE_OAUTH=true
OAUTH_CLIENT_ID=your-application-id
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_AUTH_URL=https://login.microsoftonline.com/common/oauth2/v2.0/authorize
OAUTH_TOKEN_URL=https://login.microsoftonline.com/common/oauth2/v2.0/token
OAUTH_SCOPE=https://outlook.office.com/IMAP.AccessAsUser.All,offline_access
OAUTH_CALLBACK_PORT=8080
```