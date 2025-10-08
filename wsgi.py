"""
WSGI entry point for Gunicorn
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the application directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app
from app import app as application

# Initialize database if needed
with application.app_context():
    from database import db
    from models import User, UserProfile

    # Create tables
    db.create_all()

    # Create default user if BYPASS_AUTH is enabled
    if application.config.get('BYPASS_AUTH', False):
        username = application.config.get('DEFAULT_TEST_USER', 'culurciello')
        user = User.query.filter_by(username=username).first()

        if not user:
            user = User(
                username=username,
                email=f"{username}@example.com",
                full_name=username.replace('_', ' ').title()
            )
            user.set_password('password')
            db.session.add(user)
            db.session.commit()

            # Create user profile
            profile = UserProfile(
                user_id=user.id,
                name=user.full_name.split()[0] if user.full_name else username,
                lastname=' '.join(user.full_name.split()[1:]) if user.full_name and len(user.full_name.split()) > 1 else '',
                email=user.email
            )
            db.session.add(profile)
            db.session.commit()
            print(f"✅ Created default user: {username}")

# Export the application
if __name__ == "__main__":
    application.run()
