"""
C&D Academy Registration Portal
A simple Flask application for student registration with email notification.
"""

import os
import json
import random
import logging
from datetime import datetime
from threading import Thread, Lock
from time import sleep
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message
from dotenv import load_dotenv
from email.utils import formataddr

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

# Configure Flask-Mail
logger.info("Configuring Flask-Mail with SMTP settings...")
try:
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ADDRESS')
    app.config['MAIL_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_ADDRESS')
    app.config['MAIL_TIMEOUT'] = int(os.getenv('MAIL_TIMEOUT', 15))
    
    # Validate mail configuration
    if not app.config['MAIL_USERNAME']:
        logger.error("CRITICAL: EMAIL_ADDRESS environment variable is not set")
        raise ValueError("EMAIL_ADDRESS must be set in environment variables")
    if not app.config['MAIL_PASSWORD']:
        logger.error("CRITICAL: GMAIL_APP_PASSWORD environment variable is not set")
        raise ValueError("GMAIL_APP_PASSWORD must be set in environment variables")
    
    logger.info(f"Mail configured for: {app.config['MAIL_USERNAME']}")
except Exception as e:
    logger.error(f"CRITICAL: Failed to configure Flask-Mail: {str(e)}")
    raise

mail = Mail(app)

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


def process_email_queue():
    if not os.path.exists(EMAIL_QUEUE_FILE):
        return

    with email_queue_lock:
        try:
            with open(EMAIL_QUEUE_FILE, 'r', encoding='utf-8') as f:
                queued_emails = json.load(f)
        except (json.JSONDecodeError, OSError):
            queued_emails = []

    if not queued_emails:
        return

    unsent_emails = []
    admin_email = os.getenv('ADMIN_EMAIL')
    if not admin_email:
        logger.error("Error: ADMIN_EMAIL not configured in environment variables")
        return

    for payload in queued_emails:
        try:
            subject = f"New Registration: {payload['first_name']} {payload['last_name']}"
            body = f"""
New Student Registration

Student Information:
- Name: {payload['first_name']} {payload['last_name']}
- Age: {payload['age']}
- School: {payload['school']}
- Area of Interest: {payload['area_of_interest']}

Parent/Guardian Information:
- Name: {payload['guardian_name']}
- Email: {payload['parent_email']}
- Phone: {payload['parent_phone']}

Additional Comments:
{payload['comments'] if payload['comments'] else 'None'}

---
This email was generated by the C&D Academy Registration Portal.
Queued on: {payload['queued_at']}
"""

            msg = Message(
                subject=subject,
                recipients=[admin_email],
                body=body,
                sender=app.config['MAIL_USERNAME']
            )
            mail.send(msg)
            logger.info(f"Queued registration email successfully sent for {payload['first_name']} {payload['last_name']}")
            sleep(1)
        except Exception as queue_error:
            logger.error(f"Failed to send queued registration email: {queue_error}", exc_info=True)
            unsent_emails.append(payload)

    with email_queue_lock:
        with open(EMAIL_QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(unsent_emails, f, indent=2)

try:
    process_email_queue()
except Exception as startup_queue_error:
    logger.error(f"Failed to process queued emails on startup: {startup_queue_error}", exc_info=True)


def send_registration_email(form_data):
    """
    Send registration details to administrator.
    Returns True if the send was queued or scheduled.
    """
    admin_email = os.getenv('ADMIN_EMAIL')
    if not admin_email:
        logger.error("Error: ADMIN_EMAIL not configured in environment variables")
        return False

    logger.info(f"Attempting to send registration email for {form_data['first_name']} {form_data['last_name']} to {admin_email}")

    subject = f"New Registration: {form_data['first_name']} {form_data['last_name']}"
    body = f"""
New Student Registration

Student Information:
- Name: {form_data['first_name']} {form_data['last_name']}
- Age: {form_data['age']}
- School: {form_data['school']}
- Area of Interest: {form_data['area_of_interest']}

Parent/Guardian Information:
- Name: {form_data['guardian_name']}
- Email: {form_data['parent_email']}
- Phone: {form_data['parent_phone']}

Additional Comments:
{form_data['comments'] if form_data['comments'] else 'None'}

---
This email was generated by the C&D Academy Registration Portal.
Received on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    msg = Message(
        subject=subject,
        recipients=[admin_email],
        body=body,
        sender=app.config['MAIL_USERNAME']
    )

    def send_async_email(application, message, data):
        with application.app_context():
            retry_count = int(os.getenv('MAIL_RETRY_COUNT', 2))
            retry_interval = int(os.getenv('MAIL_RETRY_INTERVAL', 5))

            for attempt in range(1, retry_count + 1):
                try:
                    mail.send(message)
                    logger.info(f"Registration email successfully sent for {data['first_name']} {data['last_name']}")
                    return
                except Exception as async_error:
                    logger.error(
                        f"Async email send attempt {attempt} failed for {data['first_name']} {data['last_name']}: {async_error}",
                        exc_info=True
                    )
                    if attempt < retry_count:
                        sleep(retry_interval)

            queue_email_data(data)

    Thread(target=send_async_email, args=(app, msg, form_data), daemon=True).start()
    return True

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
