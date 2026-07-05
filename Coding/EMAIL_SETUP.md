# Password Reset Email Setup

## Quick Start (Demo Mode - Default)

By default, the app runs in **demo mode** where password reset codes are logged to the backend console instead of being emailed. This is perfect for development and testing.

**How it works:**
1. User requests a password reset
2. A 6-digit code is generated and logged to the backend terminal/logs
3. User can see the code in the backend output: `Password reset code for user@example.com: 123456`

**No additional setup required!**

---

## Setting Up Real Email (Gmail SMTP)

If you want to send real password reset emails, follow these steps:

### Step 1: Enable 2-Step Verification
1. Go to your [Google Account Security Settings](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already enabled)

### Step 2: Generate Gmail App Password
1. Go to [App passwords](https://myaccount.google.com/apppasswords)
2. Select **Mail** and **Windows Computer** (or your device)
3. Google will generate a 16-character password (e.g., `abcd efgh ijkl mnop`)
4. **Copy this password** (without spaces)

### Step 3: Update .env File
Edit `.env` and update these fields:

```env
SMTP_USERNAME=your-gmail-address@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM_EMAIL=your-gmail-address@gmail.com
PASSWORD_RESET_ALLOW_DEMO_CODE=false
```

### Step 4: Restart Backend
Restart the FastAPI backend. Password reset emails will now be sent via Gmail.

---

## Troubleshooting

### "SMTP authentication failed"
- ✅ Verify your Gmail address is correct
- ✅ Check that the app password is 16 characters (no spaces)
- ✅ Confirm 2-Step Verification is enabled
- ✅ Try generating a new app password

### "Could not send email"
- ✅ Check your internet connection
- ✅ Verify `SMTP_HOST=smtp.gmail.com` and `SMTP_PORT=587`
- ✅ Check backend logs for detailed error message
- ✅ Enable demo mode temporarily for testing

### Want to Switch Between Email and Demo Mode?
Simply toggle `PASSWORD_RESET_ALLOW_DEMO_CODE` in `.env`:
- `PASSWORD_RESET_ALLOW_DEMO_CODE=true` → Demo mode (codes logged to backend)
- `PASSWORD_RESET_ALLOW_DEMO_CODE=false` → Email only (fails if SMTP not configured)

If email fails and demo mode is enabled, the app automatically falls back to demo mode.

---

## Using Non-Gmail Email Services

To use a different email provider (e.g., Outlook, Yahoo), update:

```env
SMTP_HOST=smtp.outlook.com        # For Outlook
SMTP_HOST=smtp.mail.yahoo.com     # For Yahoo
SMTP_PORT=587                      # Use 587 for TLS or 465 for SSL
SMTP_USERNAME=your-email@provider.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@provider.com
```

---

## Security Notes
- Never commit `.env` with real passwords to version control
- Always use app-specific passwords, not your main account password
- Keep `PASSWORD_RESET_ALLOW_DEMO_CODE=false` in production (or remove demo mode)
