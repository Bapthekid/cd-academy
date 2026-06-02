"""
C&D Academy Registration Portal
A simple Flask application for student registration with email notification.
"""

import os
import random
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message
from dotenv import load_dotenv
from email.utils import formataddr

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', True)
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

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

def send_registration_email(form_data):
    """
    Send registration details to administrator.
    Returns True if successful, False otherwise.
    """
    try:
        admin_email = os.getenv('ADMIN_EMAIL')
        if not admin_email:
            print("Error: ADMIN_EMAIL not configured in environment variables")
            return False
        
        # Create email subject and body
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
"""
        
        # Create and send email
        msg = Message(
            subject=subject,
            recipients=[admin_email],
            body=body,
            sender=os.getenv('MAIL_USERNAME')
        )
        
        mail.send(msg)
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# Routes

@app.route('/')
def home():
    """Landing page with flyer display."""
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration form page."""
    if request.method == 'GET':
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
        
        # Redirect to success page
        return redirect(url_for('success'))

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Development server - use with caution in production
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
