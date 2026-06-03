# C&D Academy Registration Portal

A simple, professional Flask web application for student registration with email notification. Students can scan a QR code, view program information, submit a registration form, and administrators receive email notifications with registration details.

## Overview

This application follows the workflow:
1. **Landing Page** - Student views flyer and academy information
2. **Registration Form** - Student enters registration details
3. **Verification** - Simple math question to prevent spam
4. **Email Notification** - Administrator receives registration details
5. **Success Page** - Confirmation message to student

## Features

✅ Clean, responsive landing page with flyer display  
✅ Comprehensive registration form with server-side validation  
✅ Simple math verification for human validation  
✅ Professional email notifications to administrator  
✅ Success confirmation page  
✅ Bootstrap 5 responsive design  
✅ Mobile-friendly interface  
✅ Security-focused form handling  
✅ Error page templates (404, 500)  

## Project Structure

```
cd-academy/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── README.md                       # This file
│
├── static/
│   ├── style.css                   # Custom CSS styling
│   └── images/
│       └── flyer.jpg              # Flyer image (add your own)
│
└── templates/
    ├── base.html                   # Base template with navbar and footer
    ├── home.html                   # Landing page
    ├── register.html               # Registration form
    ├── success.html                # Success confirmation page
    ├── 404.html                    # Page not found error
    └── 500.html                    # Server error page
```

## Tech Stack

- **Backend**: Python Flask
- **Email**: Flask-Mail
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **Environment**: python-dotenv
- **Validation**: Server-side validation with helpful error messages

## Installation & Setup

### 1. Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (optional)

### 2. Clone or Download the Project

```bash
# If using git
git clone <repository-url>
cd cd-academy

# Or download and extract the ZIP file, then navigate to the folder
```

### 3. Create and Activate Virtual Environment

**On Windows (PowerShell or Command Prompt):**
```bash
python3 -m venv venv
.\venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 5. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
# On Windows
copy .env.example .env

# On macOS/Linux
cp .env.example .env
```

Edit `.env` and configure your settings:

```env
# Flask Configuration
SECRET_KEY=your-secure-secret-key-here-change-for-production

# Email Configuration (Gmail example)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password

# Admin Email
ADMIN_EMAIL=admin@cdacademy.com

# Application Settings
APP_ENV=development
DEBUG=True
```

### 6. Email Configuration Guide

#### Using Gmail

1. Enable 2-Factor Authentication on your Google account
2. Generate an App-Specific Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer" (or your device)
   - Google will generate a 16-character password
   - Use this password as `MAIL_PASSWORD` in `.env`

3. Set `MAIL_USERNAME` to your Gmail address
4. Keep `MAIL_SERVER=smtp.gmail.com` and `MAIL_PORT=587`

#### Using Other Email Providers

Adjust `MAIL_SERVER` and `MAIL_PORT` according to your provider:

- **Outlook**: smtp.office365.com:587
- **Yahoo**: smtp.mail.yahoo.com:587
- **SendGrid**: smtp.sendgrid.net:587
- **AWS SES**: email-smtp.[region].amazonaws.com:587

### 7. Add Flyer Image

1. Create an `images` folder inside `static`:
   ```bash
   mkdir static/images
   ```

2. Place your flyer image at: `static/images/flyer.jpg`
   - Recommended size: 600x400 pixels or larger
   - Supported formats: JPG, PNG, GIF, WebP
   - If no image is found, a placeholder will be displayed

### 8. Run the Application

```bash
python3 app.py
```

The application will start on `http://localhost:5000`

### Access the Application

- **Home/Landing Page**: http://localhost:5000/
- **Registration Form**: http://localhost:5000/register

## Form Fields & Validation

### Student Information
- **First Name**: 2-50 characters, letters only
- **Last Name**: 2-50 characters, letters only
- **Age**: 5-14 years (numeric)
- **School**: 2-100 characters

### Parent/Guardian Information
- **Name**: 2-100 characters
- **Email**: Valid email format required
- **Phone**: Minimum 10 digits

### Additional
- **Area of Interest**: Required selection (Web Dev, Mobile, Data Science, AI, Cloud, Cybersecurity, Game Dev, Other)
- **Comments**: Optional, maximum 500 characters

### Verification
- **Math Question**: Simple addition/subtraction (auto-generated)

## Email Template

When a student registers, the administrator receives an email with:

```
Subject: New Registration: [Student Name]

New Student Registration

Student Information:
- Name: [First Last]
- Age: [Age]
- School: [School Name]
- Area of Interest: [Selected Area]

Parent/Guardian Information:
- Name: [Guardian Name]
- Email: [Guardian Email]
- Phone: [Guardian Phone]

Additional Comments:
[Comments or "None"]
```

## Development vs Production

### Development Mode

```env
DEBUG=True
APP_ENV=development
SECRET_KEY=dev-key-not-secure
```

### Production Mode

⚠️ **Never use these settings in production:**

1. **Change SECRET_KEY**: Use a strong, random secret key
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Set DEBUG=False**:
   ```env
   DEBUG=False
   APP_ENV=production
   SECRET_KEY=your-production-secret-key
   ```

3. **Use a production WSGI server** (not Flask's development server):
   ```bash
   pip3 install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

4. **Security checklist**:
   - [ ] SECRET_KEY is strong and random
   - [ ] DEBUG is False
   - [ ] MAIL_PASSWORD is secure and not in version control
   - [ ] ADMIN_EMAIL is correct
   - [ ] Using HTTPS (configure reverse proxy like Nginx)
   - [ ] Environment variables are set securely

## QR Code Integration

To create a QR code pointing to the registration page:

1. **QR Code Generator** (free online tools):
   - https://www.qr-code-generator.com
   - https://qr-code.tec-it.com
   - https://goqr.me

2. **Target URL**:
   ```
   https://yourdomain.com/register
   ```

3. **Test QR Code Locally**:
   - Use a QR code reader mobile app
   - Scan to verify it points to: `http://localhost:5000/register`

## Deployment Options

### Heroku
```bash
pip3 install gunicorn
heroku login
heroku create your-app-name
git push heroku main
```

### PythonAnywhere
1. Sign up at https://www.pythonanywhere.com
2. Upload your files
3. Create a Web app pointing to WSGI file
4. Configure environment variables in Web tab

### AWS, Azure, Google Cloud
Use their Python/Flask deployment guides for Docker or direct deployment.

## Troubleshooting

### Email Not Sending

1. **Check Gmail credentials**:
   - Verify app-specific password is correct
   - Check 2FA is enabled
   - Verify 16-character password (not your regular password)

2. **Check email configuration**:
   ```python
   # Add to app.py temporarily for debugging
   with app.app_context():
       msg = Message('Test', recipients=['test@example.com'], body='Test')
       mail.send(msg)
   ```

3. **Check firewall/proxy**: Some networks block SMTP. Try different MAIL_PORT or MAIL_SERVER.

### Form Validation Errors

- Check browser console for client-side errors
- Server-side validation provides clear error messages
- Ensure field values match validation requirements

### Template Not Found

- Verify templates are in `templates/` folder (case-sensitive)
- Check file names match exactly (home.html, register.html, success.html, base.html)

### Flyer Image Not Showing

- Place flyer.jpg in `static/images/` folder
- Verify correct file name and extension
- Check file permissions (readable)
- Use absolute path if needed in templates

## Future Enhancements

This is Version 1 - suitable for basic registration needs. Potential future features:

- [ ] Database storage for registrations
- [ ] User authentication for admin dashboard
- [ ] Admin panel to view/export registrations
- [ ] Attendance tracking
- [ ] PDF export of registrations
- [ ] Multi-language support
- [ ] Participant QR codes/attendance scanning
- [ ] Payment integration
- [ ] Email templates customization

## Security Considerations

- ✅ Server-side validation on all form inputs
- ✅ XSS protection via Jinja2 templating
- ✅ CSRF protection via Flask sessions
- ✅ Email validation
- ✅ Phone number validation
- ✅ Human verification (math question)
- ✅ Secure session handling
- ⚠️ Use HTTPS in production
- ⚠️ Never commit `.env` file to version control (it's in `.gitignore`)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home/landing page |
| GET | `/register` | Registration form (initial load) |
| POST | `/register` | Submit registration form |
| GET | `/success` | Success confirmation page |

## File Sizes & Performance

- **CSS**: ~8 KB (minifiable)
- **Static Assets**: ~50 KB (flyer image varies)
- **Load Time**: < 2 seconds on typical connection
- **Bootstrap**: Served via CDN (faster loading)

## Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## License

This project is provided as-is for educational and commercial use.

## Support & Contact

For questions or issues:
- 📧 Email: info@cdacademy.com
- 📞 Phone: (555) 123-4567
- 📍 Location: 123 Education St., Tech City, TC 12345

## Changelog

### Version 1.0 (Initial Release)
- Landing page with flyer display
- Registration form with comprehensive validation
- Email notifications to administrator
- Success confirmation page
- Responsive Bootstrap 5 design
- Human verification (math questions)
- Environment variable configuration
- Error page templates

---

**Built with ❤️ by C&D Academy Development Team**