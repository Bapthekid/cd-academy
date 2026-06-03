"""
C&D Academy Registration Portal
A simple Flask application for student registration with email notification.
"""

import os
import json
import random
import logging
from datetime import datetime
from threading import Lock
from time import sleep
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message
from dotenv import load_dotenv
from email.utils import formataddr
import socket
import requests

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Durable email queue file for retrying failed sends
EMAIL_QUEUE_FILE = os.path.join(os.path.dirname(__file__), 'email_queue.json')
email_queue_lock = Lock()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key:
    logger.error("CRITICAL: SECRET_KEY environment variable is not set")
    raise ValueError("SECRET_KEY must be set in environment variables")

# Configure Flask-Mail (SMTP is optional when using HTTP email providers on Render)
logger.info("Configuring email settings...")
try:
    has_smtp_creds = bool(os.getenv('EMAIL_ADDRESS') and os.getenv('GMAIL_APP_PASSWORD'))
    has_http_email = bool(os.getenv('SENDGRID_API_KEY') or os.getenv('RESEND_API_KEY'))

    if not has_smtp_creds and not has_http_email:
        raise ValueError(
            "Email not configured. Set Gmail SMTP (EMAIL_ADDRESS + GMAIL_APP_PASSWORD) "
            "or an HTTP provider (SENDGRID_API_KEY or RESEND_API_KEY). "
            "Render and most cloud hosts block SMTP; use SendGrid in production."
        )

    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ADDRESS') or os.getenv('ADMIN_EMAIL')
    app.config['MAIL_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = (
        os.getenv('EMAIL_ADDRESS')
        or os.getenv('RESEND_FROM_EMAIL')
        or os.getenv('ADMIN_EMAIL')
    )
    app.config['MAIL_TIMEOUT'] = int(os.getenv('MAIL_TIMEOUT', 15))

    if has_smtp_creds:
        logger.info(f"SMTP mail configured for: {app.config['MAIL_USERNAME']}")
    if has_http_email:
        providers = []
        if os.getenv('SENDGRID_API_KEY'):
            providers.append('SendGrid')
        if os.getenv('RESEND_API_KEY'):
            providers.append('Resend')
        logger.info(f"HTTP email provider(s) configured: {', '.join(providers)}")
except Exception as e:
    logger.error(f"CRITICAL: Failed to configure email: {str(e)}")
    raise

mail = Mail(app)

if os.getenv('APP_ENV', '').lower() == 'production' and not (
    os.getenv('SENDGRID_API_KEY') or os.getenv('RESEND_API_KEY')
):
    logger.warning(
        "Production mode without SENDGRID_API_KEY or RESEND_API_KEY. "
        "SMTP is blocked on Render; registration emails will fail until an HTTP provider is configured."
    )

# Helper function to generate a simple math question for verification
def generate_verification_question():
    """Generate a simple math question for human verification."""
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(['+', '-'])
    
    if operation == '+':
        answer = num1 + num2
        question = f"{num1} + {num2}"
    else:
        # Ensure positive result
        if num1 >= num2:
            answer = num1 - num2
            question = f"{num1} - {num2}"
        else:
            answer = num2 - num1
            question = f"{num2} - {num1}"
    
    return question, str(answer)

# Server-side validation functions
def validate_form_data(data):
    """
    Validate registration form data.
    Returns (is_valid, error_messages)
    """
    errors = []
    
    # First Name validation
    first_name = data.get('first_name', '').strip()
    if not first_name:
        errors.append("First name is required.")
    elif len(first_name) < 2:
        errors.append("First name must be at least 2 characters.")
    elif len(first_name) > 50:
        errors.append("First name must not exceed 50 characters.")
    elif not first_name.replace(" ", "").replace("-", "").isalpha():
        errors.append("First name can only contain letters, spaces, and hyphens.")
    
    # Last Name validation
    last_name = data.get('last_name', '').strip()
    if not last_name:
        errors.append("Last name is required.")
    elif len(last_name) < 2:
        errors.append("Last name must be at least 2 characters.")
    elif len(last_name) > 50:
        errors.append("Last name must not exceed 50 characters.")
    elif not last_name.replace(" ", "").replace("-", "").isalpha():
        errors.append("Last name can only contain letters, spaces, and hyphens.")
    
    # Age validation
    try:
        age = int(data.get('age', 0))
        if age < 5 or age > 25:
            errors.append("Age must be between 5 and 25.")
    except ValueError:
        errors.append("Please enter a valid age as a number.")
    
    # School validation
    school = data.get('school', '').strip()
    if not school:
        errors.append("School is required.")
    elif len(school) < 2:
        errors.append("School name must be at least 2 characters.")
    elif len(school) > 100:
        errors.append("School name must not exceed 100 characters.")
    
    # Guardian Name validation
    guardian_name = data.get('guardian_name', '').strip()
    if not guardian_name:
        errors.append("Parent/Guardian name is required.")
    elif len(guardian_name) < 2:
        errors.append("Parent/Guardian name must be at least 2 characters.")
    elif len(guardian_name) > 100:
        errors.append("Parent/Guardian name must not exceed 100 characters.")
    
    # Email validation
    parent_email = data.get('parent_email', '').strip()
    if not parent_email:
        errors.append("Parent email is required.")
    elif '@' not in parent_email or '.' not in parent_email:
        errors.append("Please enter a valid email address.")
    elif len(parent_email) > 120:
        errors.append("Email is too long.")
    
    # Phone validation
    phone = data.get('parent_phone', '').strip()
    if not phone:
        errors.append("Parent phone number is required.")
    elif len(phone) < 10:
        errors.append("Phone number must be at least 10 digits.")
    elif not any(c.isdigit() for c in phone):
        errors.append("Phone number must contain at least one digit.")
    elif len(phone) > 20:
        errors.append("Phone number is too long.")
    
    # Area of Interest validation
    area_of_interest = data.get('area_of_interest', '').strip()
    if not area_of_interest:
        errors.append("Please select an area of interest.")
    
    # Additional Comments validation (optional, but has length limit)
    comments = data.get('comments', '').strip()
    if len(comments) > 500:
        errors.append("Comments must not exceed 500 characters.")
    
    return len(errors) == 0, errors

def queue_email_data(form_data):
    payload = {
        'first_name': form_data['first_name'],
        'last_name': form_data['last_name'],
        'age': form_data['age'],
        'school': form_data['school'],
        'area_of_interest': form_data['area_of_interest'],
        'guardian_name': form_data['guardian_name'],
        'parent_email': form_data['parent_email'],
        'parent_phone': form_data['parent_phone'],
        'comments': form_data['comments'],
        'queued_at': datetime.utcnow().isoformat() + 'Z'
    }

    with email_queue_lock:
        queued_emails = []
        try:
            if os.path.exists(EMAIL_QUEUE_FILE):
                with open(EMAIL_QUEUE_FILE, 'r', encoding='utf-8') as f:
                    queued_emails = json.load(f)
        except (json.JSONDecodeError, OSError):
            queued_emails = []

        queued_emails.append(payload)

        with open(EMAIL_QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(queued_emails, f, indent=2)

    logger.warning("Queued registration email for retry later due to send failure.")


def format_registration_email_body(data, *, received_on=None, queued_on=None):
    """Build the plain-text body for a registration notification email."""
    footer_lines = [
        "---",
        "This email was generated by the C&D Academy Registration Portal.",
    ]
    if received_on:
        footer_lines.append(f"Received on: {received_on}")
    if queued_on:
        footer_lines.append(f"Queued on: {queued_on}")

    return f"""
New Student Registration

Student Information:
- Name: {data['first_name']} {data['last_name']}
- Age: {data['age']}
- School: {data['school']}
- Area of Interest: {data['area_of_interest']}

Parent/Guardian Information:
- Name: {data['guardian_name']}
- Email: {data['parent_email']}
- Phone: {data['parent_phone']}

Additional Comments:
{data['comments'] if data['comments'] else 'None'}

{chr(10).join(footer_lines)}
"""


def build_registration_message(form_data, admin_email):
    """Create a Flask-Mail Message for a registration notification."""
    subject = f"New Registration: {form_data['first_name']} {form_data['last_name']}"
    received_on = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    queued_on = form_data.get('queued_at')
    body = format_registration_email_body(
        form_data,
        received_on=received_on if not queued_on else None,
        queued_on=queued_on,
    )
    return Message(
        subject=subject,
        recipients=[admin_email],
        body=body,
        sender=app.config['MAIL_USERNAME'],
    )


def has_http_email_provider():
    """True when an HTTPS email API is configured (works on Render; SMTP ports are blocked)."""
    return bool(os.getenv('SENDGRID_API_KEY') or os.getenv('RESEND_API_KEY'))


def smtp_disabled():
    """
    Return True when SMTP should not be attempted.
    Cloud hosts like Render block outbound ports 25/465/587.
    """
    if os.getenv('DISABLE_SMTP', '').lower() == 'true':
        return True
    if os.getenv('FORCE_SMTP', '').lower() == 'true':
        return False
    if os.getenv('APP_ENV', '').lower() == 'production':
        return True
    return False


def has_smtp_credentials():
    return bool(os.getenv('EMAIL_ADDRESS') and os.getenv('GMAIL_APP_PASSWORD'))


def attempt_send_registration_email(form_data):
    """
    Try to deliver a registration email via HTTP API (SendGrid/Resend) or SMTP.
    Does not queue on failure. Returns True if delivered, False otherwise.
    """
    admin_email = os.getenv('ADMIN_EMAIL')
    if not admin_email:
        logger.error("Error: ADMIN_EMAIL not configured in environment variables")
        return False

    # HTTP APIs use port 443 and work on Render; try these first in production.
    if has_http_email_provider():
        if send_via_http_email(form_data):
            return True
        if smtp_disabled():
            logger.error(
                "HTTP email delivery failed and SMTP is disabled in production. "
                "Verify SENDGRID_API_KEY / RESEND_API_KEY and sender verification."
            )
            return False

    if smtp_disabled():
        logger.error(
            "SMTP is blocked on this host (typical for Render). "
            "Add SENDGRID_API_KEY to environment variables. "
            "See DEPLOYMENT.md for setup steps."
        )
        return False

    if not has_smtp_credentials():
        logger.error("SMTP credentials (EMAIL_ADDRESS + GMAIL_APP_PASSWORD) are not configured.")
        return False

    message = build_registration_message(form_data, admin_email)
    host = app.config.get('MAIL_SERVER')
    port = app.config.get('MAIL_PORT')
    timeout = app.config.get('MAIL_TIMEOUT', 15)

    smtp_available = False
    try:
        smtp_available = can_connect_smtp(host, port, timeout=timeout)
    except Exception as pre_err:
        logger.error(f"SMTP preflight check failed: {pre_err}", exc_info=True)
        smtp_available = False

    if not smtp_available:
        logger.warning(f"SMTP server {host}:{port} unreachable; trying HTTP email if configured.")
        return send_via_http_email(form_data)

    retry_count = int(os.getenv('MAIL_RETRY_COUNT', 2))
    retry_interval = int(os.getenv('MAIL_RETRY_INTERVAL', 5))

    for attempt in range(1, retry_count + 1):
        try:
            mail.send(message)
            logger.info(
                f"Registration email successfully sent for {form_data['first_name']} {form_data['last_name']}"
            )
            return True
        except Exception as send_error:
            logger.error(
                f"Email send attempt {attempt} failed for {form_data['first_name']} {form_data['last_name']}: {send_error}",
                exc_info=True,
            )
            if attempt < retry_count:
                sleep(retry_interval)

    return send_via_http_email(form_data)


def process_email_queue():
    """Process queued emails, atomically dequeuing to avoid duplicate sends."""
    with email_queue_lock:
        if not os.path.exists(EMAIL_QUEUE_FILE):
            return

        try:
            with open(EMAIL_QUEUE_FILE, 'r', encoding='utf-8') as f:
                queued_emails = json.load(f)
        except (json.JSONDecodeError, OSError):
            queued_emails = []

        if not queued_emails:
            return

        # Clear the queue before releasing the lock so concurrent workers cannot
        # read and send the same payloads.
        with open(EMAIL_QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)

    unsent_emails = []
    for payload in queued_emails:
        try:
            if attempt_send_registration_email(payload):
                logger.info(
                    f"Queued registration email successfully sent for {payload['first_name']} {payload['last_name']}"
                )
                sleep(1)
            else:
                unsent_emails.append(payload)
        except Exception as queue_error:
            logger.error(f"Failed to send queued registration email: {queue_error}", exc_info=True)
            unsent_emails.append(payload)

    if not unsent_emails:
        return

    with email_queue_lock:
        current_queue = []
        if os.path.exists(EMAIL_QUEUE_FILE):
            try:
                with open(EMAIL_QUEUE_FILE, 'r', encoding='utf-8') as f:
                    current_queue = json.load(f)
            except (json.JSONDecodeError, OSError):
                current_queue = []

        current_queue.extend(unsent_emails)

        with open(EMAIL_QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_queue, f, indent=2)


def can_connect_smtp(host, port, timeout=5):
    """Check basic SMTP connectivity (DNS + TCP) without performing SMTP handshake."""
    try:
        socket.gethostbyname(host)
    except Exception as e:
        logger.error(f"SMTP DNS resolution failed for {host}: {e}")
        return False

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception as e:
        logger.error(f"SMTP TCP connect failed to {host}:{port}: {e}")
        return False


def send_via_http_email(data):
    """Try SendGrid, then Resend. Returns True if any provider succeeds."""
    if send_via_sendgrid(data):
        return True
    return send_via_resend(data)


def send_via_sendgrid(data):
    """Attempt to send email via SendGrid API if configured. Returns True on success."""
    api_key = os.getenv('SENDGRID_API_KEY')
    admin_email = os.getenv('ADMIN_EMAIL')
    if not api_key or not admin_email:
        return False

    url = 'https://api.sendgrid.com/v3/mail/send'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    subject = f"New Registration: {data['first_name']} {data['last_name']}"
    content_text = format_registration_email_body(
        data,
        received_on=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )

    payload = {
        'personalizations': [
            {
                'to': [{'email': admin_email}],
                'subject': subject
            }
        ],
        'from': {'email': app.config.get('MAIL_DEFAULT_SENDER', admin_email)},
        'content': [{'type': 'text/plain', 'value': content_text}]
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code in (200, 202):
            logger.info(f"SendGrid email sent for {data['first_name']} {data['last_name']}")
            return True
        else:
            logger.error(f"SendGrid send failed: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"SendGrid send exception: {e}", exc_info=True)
        return False


def send_via_resend(data):
    """Attempt to send email via Resend API if configured. Returns True on success."""
    api_key = os.getenv('RESEND_API_KEY')
    admin_email = os.getenv('ADMIN_EMAIL')
    from_email = os.getenv('RESEND_FROM_EMAIL') or app.config.get('MAIL_DEFAULT_SENDER')
    if not api_key or not admin_email or not from_email:
        return False

    subject = f"New Registration: {data['first_name']} {data['last_name']}"
    content_text = format_registration_email_body(
        data,
        received_on=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )

    payload = {
        'from': from_email,
        'to': [admin_email],
        'subject': subject,
        'text': content_text,
    }

    try:
        resp = requests.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            logger.info(f"Resend email sent for {data['first_name']} {data['last_name']}")
            return True
        logger.error(f"Resend send failed: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Resend send exception: {e}", exc_info=True)
        return False


try:
    process_email_queue()
except Exception as startup_queue_error:
    logger.error(f"Failed to process queued emails on startup: {startup_queue_error}", exc_info=True)


def send_registration_email(form_data):
    """
    Send registration details to administrator.
    Returns True only if the email was delivered (SMTP, SendGrid, or Resend).
    Returns False if delivery failed and the registration was queued for retry.
    """
    admin_email = os.getenv('ADMIN_EMAIL')
    if not admin_email:
        logger.error("Error: ADMIN_EMAIL not configured in environment variables")
        return False

    logger.info(
        f"Attempting to send registration email for {form_data['first_name']} {form_data['last_name']} to {admin_email}"
    )

    if attempt_send_registration_email(form_data):
        return True

    logger.warning(
        f"Registration email delivery failed for {form_data['first_name']} {form_data['last_name']}; queuing for retry."
    )
    queue_email_data(form_data)
    return False

# Routes

@app.before_request
def log_request():
    """Log incoming requests for debugging."""
    logger.debug(f"{request.method} {request.path}")

@app.route('/')
def home():
    """Landing page with flyer display."""
    logger.info("Home page accessed")
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration form page."""
    if request.method == 'GET':
        logger.info("Registration form requested")
        # Generate new verification question
        question, answer = generate_verification_question()
        session['verification_answer'] = answer
        session['verification_question'] = question
        
        return render_template('register.html', 
                             form_data={},
                             question=question,
                             areas_of_interest=[
                                 'Speed',
                                 'Agility',
                                 'Coordination',
                                 'Strength',
                                 'Confidence'
                             ])
    
    elif request.method == 'POST':
        logger.info("Registration form submitted")
        # Verify human verification answer
        user_answer = request.form.get('verification_answer', '').strip()
        correct_answer = session.get('verification_answer', '')
        
        if user_answer != correct_answer:
            # Re-generate question and show error
            question, answer = generate_verification_question()
            session['verification_answer'] = answer
            session['verification_question'] = question
            
            return render_template('register.html',
                                 error="Verification answer is incorrect. Please try again.",
                                 question=question,
                                 areas_of_interest=[
                                     'Speed',
                                     'Agility',
                                     'Coordination',
                                     'Strength',
                                     'Confidence'
                                 ])
        
        # Validate form data
        form_data = {
            'first_name': request.form.get('first_name', '').strip(),
            'last_name': request.form.get('last_name', '').strip(),
            'age': request.form.get('age', '').strip(),
            'school': request.form.get('school', '').strip(),
            'guardian_name': request.form.get('guardian_name', '').strip(),
            'parent_email': request.form.get('parent_email', '').strip(),
            'parent_phone': request.form.get('parent_phone', '').strip(),
            'area_of_interest': request.form.get('area_of_interest', '').strip(),
            'comments': request.form.get('comments', '').strip()
        }
        
        is_valid, errors = validate_form_data(form_data)
        
        if not is_valid:
            # Show validation errors
            question = session.get('verification_question', '')
            question, answer = generate_verification_question()
            session['verification_answer'] = answer
            session['verification_question'] = question
            
            return render_template('register.html',
                                 error="Please fix the following errors: " + " ".join(errors),
                                 form_data=form_data,
                                 question=question,
                                 areas_of_interest=[
                                     'Speed',
                                     'Agility',
                                     'Coordination',
                                     'Strength',
                                     'Confidence'
                                 ])
        
        # Send email notification
        email_sent = send_registration_email(form_data)
        
        if not email_sent:
            question, answer = generate_verification_question()
            session['verification_answer'] = answer
            session['verification_question'] = question
            return render_template('register.html',
                                   error="There was an issue sending your registration. Please try again later.",
                                   form_data=form_data,
                                   question=question,
                                   areas_of_interest=[
                                       'Speed',
                                       'Agility',
                                       'Coordination',
                                       'Strength',
                                       'Confidence'
                                   ])

        # Redirect to success page
        return redirect(url_for('success'))

@app.route('/success')
def success():
    """Successful registration confirmation page."""
    logger.info("Success page displayed - registration completed")
    return render_template('success.html')

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 error: {request.path} not found")
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error(f"500 error: {str(error)}", exc_info=True)
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Get configuration from environment variables
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 10000))
    
    logger.info(f"Starting C&D Academy application...")
    logger.info(f"Configuration: DEBUG={debug_mode}, HOST={host}, PORT={port}")
    logger.info(f"Environment: {os.getenv('APP_ENV', 'production')}")
    
    # WARNING: In production, use Gunicorn instead of Flask development server
    if debug_mode:
        logger.warning("DEBUG mode is enabled - do NOT use this in production!")
        app.run(debug=True, host=host, port=port)
    else:
        logger.info("Running in production mode - use Gunicorn")
        app.run(debug=False, host=host, port=port)
