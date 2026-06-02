# Email Sharing Setup Guide

## Overview
Email Sharing allows users to send generated presentations directly to recipients via email with the PPTX file attached.

## Configuration

### 1. Add Email Credentials to `.env`

Create or update your `.env` file in the `backend/` directory with:

```env
# Email Configuration (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# For other email providers:
# Outlook: SMTP_SERVER=smtp-mail.outlook.com
# Yahoo: SMTP_SERVER=smtp.mail.yahoo.com
```

### 2. Gmail Setup (Recommended)

#### Option A: Gmail App Password (Recommended)
1. Enable 2-Factor Authentication on your Google Account
2. Go to [Google Account Settings](https://myaccount.google.com/apppasswords)
3. Select "Mail" and "Windows Computer" (or your device)
4. Google will generate a 16-character app password
5. Use this password in `SENDER_PASSWORD` in `.env`

#### Option B: Less Secure Apps
1. Go to [Google Account Settings](https://myaccount.google.com/lesssecureapps)
2. Enable "Less secure app access"
3. Use your regular Gmail password in `SENDER_PASSWORD`

### 3. Other Email Providers

**Outlook/Microsoft:**
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SENDER_EMAIL=your-email@outlook.com
SENDER_PASSWORD=your-password
```

**Yahoo:**
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SENDER_EMAIL=your-email@yahoo.com
SENDER_PASSWORD=your-app-password  # Yahoo also requires app passwords
```

## Usage

1. Generate a presentation in Presenton
2. SlideViewer opens automatically
3. Click the **"📧 Share"** button in the top-right (next to Export PPT)
4. Enter recipient email addresses (comma-separated for multiple)
5. (Optional) Customize subject and message
6. Click **"Send Email"**
7. Presentation PPTX file will be sent to all recipients

## Features

✅ Send to multiple recipients at once (comma-separated)
✅ Customize email subject and message
✅ Presentation file attached automatically
✅ Error handling and validation
✅ Responsive design on desktop and mobile
✅ Real-time feedback (success/error messages)

## Security Notes

⚠️ **Never commit `.env` file to Git** - Add it to `.gitignore`
⚠️ **Use App Passwords** - Don't use your main account password if possible
⚠️ **Credentials in Environment** - Keep credentials secure in production
⚠️ **HTTPS in Production** - Always use HTTPS when deploying to production

## Troubleshooting

### "Email credentials not configured"
- Ensure `SENDER_EMAIL` and `SENDER_PASSWORD` are set in `.env`
- Restart the backend server after updating `.env`

### "Email authentication failed"
- Verify credentials are correct
- For Gmail, check if you're using an App Password (not regular password with 2FA)
- Ensure "Less Secure Apps" is enabled if not using App Password

### "SMTP error" / Connection issues
- Check `SMTP_SERVER` and `SMTP_PORT` are correct
- Ensure your firewall allows outbound SMTP connections
- Try port 465 instead of 587 (may require SSL)

### Email not received
- Check recipient email address is correct
- Check spam/junk folder
- Verify PPTX file was attached to the email
- Check backend console logs for errors

## API Reference

**Endpoint:** `POST /share/email`

**Request:**
```json
{
  "pptx_path": "presentations/pres_20260518_120000.pptx",
  "recipient_emails": ["user@example.com", "another@example.com"],
  "subject": "Check out this presentation!",
  "message": "Hi, please see the attached presentation.",
  "presentation_title": "My Awesome Presentation"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Sent to 2 recipient(s)",
  "sent_to": 2
}
```

## Future Enhancements

Potential improvements for future versions:
- Cloud storage integration (Google Drive, OneDrive)
- Scheduling email sends
- Email templates and branding
- Delivery tracking and analytics
- Calendar invitations with presentation link
- PDF export option for email
