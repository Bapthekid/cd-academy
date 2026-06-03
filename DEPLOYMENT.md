# C&D Academy - Render Deployment Guide

## Overview
This guide provides step-by-step instructions to deploy the C&D Academy Flask application on Render.com using Docker.

## Prerequisites
- GitHub account with the C&D Academy repository pushed
- Render.com account
- Gmail account with 2FA enabled (for email configuration)

## Pre-Deployment Checklist

✅ **app.py Configuration**
- Application binds to `0.0.0.0` on dynamic port from `PORT` environment variable
- All secrets loaded from environment variables (no hardcoded values)
- Comprehensive error logging configured
- Production-ready with Gunicorn support
- Supports both Flask development mode and production Gunicorn mode

✅ **Dockerfile**
- Multi-stage build optimized for production
- Non-root user (`appuser`) for security
- Health checks enabled
- Gunicorn configured with 4 workers
- Port 10000 exposed (override with PORT env var if needed)

✅ **Dependencies**
- requirements.txt updated with all necessary packages
- Gunicorn included for production deployment
- All pinned to specific versions for reproducibility

✅ **Environment Configuration**
- .env.example updated with all required variables
- .env file excluded from Git (already in .gitignore)
- No secrets hardcoded in any file

## Step 1: Prepare GitHub Repository

### 1.1 Remove .env from Git History (if accidentally committed)
```powershell
# Navigate to your project directory
cd c:\Users\danie\cd-academy

# Verify .env is in .gitignore
cat .gitignore | grep ".env"

# If .env was previously committed, remove it:
git rm --cached .env
git commit -m "Remove .env from version control"
git push origin main
```

### 1.2 Verify All Deployment Files Are Committed
```powershell
git status

# You should see these NEW files ready to commit:
# - Dockerfile
# - .dockerignore
# - render.yaml
# - DEPLOYMENT.md

# Commit all changes
git add Dockerfile .dockerignore render.yaml DEPLOYMENT.md app.py requirements.txt .env.example
git commit -m "Prepare application for Render deployment

- Add production-ready Dockerfile with Gunicorn
- Add .dockerignore for efficient builds
- Add render.yaml configuration
- Update app.py with environment variables and logging
- Update requirements.txt with pinned versions
- Update .env.example with correct variable names"

git push origin main
```

## Step 2: Create Environment Variables on Render

### 2.1 Generate Required Secrets

**Secret Key:**
```python
python -c "import secrets; print(secrets.token_hex(32))"
# Example output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

### 2.2 SendGrid Setup (Required on Render — SMTP Is Blocked)

Render blocks outbound SMTP (ports 25, 465, 587). Gmail SMTP will **not** work in production. Use SendGrid over HTTPS instead:

1. Create a free account at [sendgrid.com](https://sendgrid.com)
2. Go to **Settings → API Keys** → Create API Key (Full Access or Restricted with Mail Send)
3. Go to **Settings → Sender Authentication → Single Sender Verification**
4. Add and verify the email address you want emails to come from (e.g. `clardo2922@gmail.com`)
5. Copy the API key — you will set it as `SENDGRID_API_KEY` on Render

**Important:** The verified Single Sender address should match `EMAIL_ADDRESS` in your environment variables.

### 2.3 Gmail App Password (Local Development Only)

For running `python app.py` on your computer:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication → App passwords
3. Use the 16-character password as `GMAIL_APP_PASSWORD`

This is **not** used on Render when `APP_ENV=production`.

### 2.4 Create Render Service

1. Go to [render.com](https://render.com) and sign in
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Fill in the deployment settings:

   **Basic Settings:**
   - Name: `cd-academy` (or your preferred name)
   - Environment: `Docker`
   - Region: Choose closest to your users
   - Branch: `main`

   **Build Settings:**
   - Dockerfile Path: `./Dockerfile`
   - Docker Context: `./`

## Step 3: Configure Environment Variables on Render

In the Render dashboard, go to your service → Environment:

### Required Environment Variables:

```
SECRET_KEY=<your-generated-secret-key>
ADMIN_EMAIL=<admin-email-address>
EMAIL_ADDRESS=<your-verified-sendgrid-sender>
SENDGRID_API_KEY=<your-sendgrid-api-key>
APP_ENV=production
DEBUG=False
HOST=0.0.0.0
```

**Where:**
- `SECRET_KEY`: Generate using the Python command above
- `ADMIN_EMAIL`: Where registration notifications are delivered (e.g. `clardo2922@gmail.com`)
- `EMAIL_ADDRESS`: Must match your **verified SendGrid Single Sender** address
- `SENDGRID_API_KEY`: API key from SendGrid (required on Render)
- `APP_ENV`: Must be `production` (enables HTTP email, skips blocked SMTP)
- `DEBUG`: Must be `False` in production

`GMAIL_APP_PASSWORD` is optional on Render and only needed for local SMTP testing.

## Step 4: Deploy

### 4.1 Using Render Dashboard
1. Click "Deploy latest" on your service page
2. Wait for build to complete (usually 2-5 minutes)
3. Check the logs for any errors

### 4.2 Using Git Push (Automatic)
Once configured, any push to your main branch triggers automatic deployment:

```powershell
git add .
git commit -m "Update application"
git push origin main
```

## Step 5: Monitor Deployment

1. Open the **Logs** tab in your Render service
2. Look for initialization messages like:
   ```
   Starting C&D Academy application...
   Configuration: DEBUG=False, HOST=0.0.0.0, PORT=10000
   Environment: production
   HTTP email provider(s) configured: SendGrid
   ```

3. Check for errors related to:
   - Missing environment variables
   - Email authentication failures
   - Database connection issues

## Step 6: Verify Deployment

Once deployed (status shows "Live"):

1. Click the URL provided by Render
2. Test the home page loads correctly
3. Submit a test registration form
4. Verify the admin email receives the notification

## Troubleshooting

### Build Fails: "Cannot find module X"
- Ensure all imports are included in requirements.txt
- Check Python version compatibility (using 3.11)
- Verify no circular imports in code

### Application Starts but Won't Accept Connections
- Check PORT environment variable is set
- Verify HOST is `0.0.0.0` (not localhost)
- Look for binding errors in logs

### Email Not Sending

**Log: `SMTP TCP connect failed ... Network is unreachable`**
→ Expected on Render. Add `SENDGRID_API_KEY` and redeploy. Gmail SMTP cannot be used on Render.

**Log: `SMTP is blocked on this host`**
→ Set `SENDGRID_API_KEY` in Render environment variables (see Step 2.2).

**Log: `SendGrid send failed: 403`**
→ Verify your sender in SendGrid (Single Sender Verification) and ensure `EMAIL_ADDRESS` matches.

```
Error: ADMIN_EMAIL not configured
→ Add ADMIN_EMAIL to Render environment variables

Error: Email not configured
→ Add SENDGRID_API_KEY (production) or EMAIL_ADDRESS + GMAIL_APP_PASSWORD (local)
```

### 500 Errors on Form Submission
1. Check Render logs for detailed error messages
2. Ensure MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS are correct
3. Verify Gmail app password hasn't expired (regenerate if needed)

### Static Files Not Loading
- Verify `static/` directory structure matches Dockerfile expectations
- Check that CSS/images paths use `{{ url_for('static', filename='...') }}`

## Environment Variables Reference

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| SECRET_KEY | Yes | `a1b2c3...` | Generate with Python secrets module |
| SENDGRID_API_KEY | Yes (Render) | `SG.xxx` | Required on Render; SMTP is blocked |
| EMAIL_ADDRESS | Yes | `yourname@gmail.com` | Must match SendGrid verified sender |
| ADMIN_EMAIL | Yes | `admin@example.com` | Where registration emails go |
| GMAIL_APP_PASSWORD | Local only | `abcd efgh ijkl mnop` | Gmail app password for local dev |
| RESEND_API_KEY | No | `re_xxx` | Alternative to SendGrid |
| APP_ENV | Yes | `production` | Always use "production" |
| DEBUG | Yes | `False` | Always use "False" in production |
| HOST | No | `0.0.0.0` | Default: 0.0.0.0 |
| PORT | No | `10000` | Set by Render automatically |
| MAIL_SERVER | No | `smtp.gmail.com` | Default: smtp.gmail.com |
| MAIL_PORT | No | `587` | Default: 587 |
| MAIL_USE_TLS | No | `True` | Default: True |

## File Changes Summary

### app.py
- Added logging throughout application
- Updated configuration to require environment variables
- Changed EMAIL_ADDRESS and GMAIL_APP_PASSWORD variable names
- Updated PORT and HOST to use environment variables
- Added @app.before_request decorator for request logging
- Added logging to error handlers

### Dockerfile (NEW)
- Production-ready multi-stage build
- Non-root user for security
- Health checks configured
- Gunicorn startup with 4 workers

### .dockerignore (NEW)
- Excludes unnecessary files from Docker build
- Reduces image size and build time

### render.yaml (NEW)
- Render deployment configuration
- Specifies Python version, build command, start command
- Declares environment variables

### requirements.txt
- Added Werkzeug for dependency completeness
- Pinned all versions for reproducibility

### .env.example
- Updated variable names (EMAIL_ADDRESS, GMAIL_APP_PASSWORD)
- Added documentation for each variable
- Added port and host configuration

## Rollback Procedure

If deployment fails:

1. Render dashboard → Service Settings → Restart Instance
2. Check logs for specific error messages
3. Update environment variables if needed
4. Click "Deploy latest" to retry
5. For code changes, fix locally and push to GitHub:
   ```powershell
   git add .
   git commit -m "Fix deployment issue"
   git push origin main
   ```

## Performance Tuning

Current Dockerfile uses:
- 4 Gunicorn workers
- 30-second timeout
- Sync worker class

For high traffic:
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "8", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
```

**Note:** Requires `uvicorn` in requirements.txt for async workers.

## Security Checklist

✅ No hardcoded secrets in any file
✅ .env excluded from Git
✅ Non-root user in Docker container
✅ All environment variables required for production
✅ DEBUG mode disabled in production
✅ Logging configured for troubleshooting
✅ Health checks configured
✅ Input validation on registration form

## Success Criteria

Your deployment is successful when:
1. ✅ Application loads without errors (Render shows "Live" status)
2. ✅ Home page displays correctly
3. ✅ Registration form submits successfully
4. ✅ Admin receives registration email
5. ✅ No error logs related to missing environment variables
6. ✅ Static files (CSS, images) load correctly
7. ✅ 404 and 500 error pages work

## Next Steps

After successful deployment:
1. Test with real form submissions
2. Monitor email delivery
3. Check Render logs regularly for errors
4. Set up error notifications (Render offers integration options)
5. Plan scaling if traffic increases

## Support & Debugging

For detailed logs:
```
Render Dashboard → Your Service → Logs tab
```

Check for these indicators:
- "Mail configured for:" - Confirms email setup
- "Configuration: DEBUG=False" - Confirms production mode
- "New registration" messages - Confirms form processing

---

**Document Version:** 1.0
**Last Updated:** 2026-06-02
**Deployment Platform:** Render.com
