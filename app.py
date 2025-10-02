from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler

from database import db

load_dotenv()

# Configure logging
def setup_logging():
    """Set up application logging to file and console."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Create app logger
    app_logger = logging.getLogger('orb')
    app_logger.setLevel(logging.INFO)

    return app_logger

# Set up logging
logger = setup_logging()

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='TheOrb Web Application')
    parser.add_argument('--bypass-auth', action='store_true',
                        help='Bypass authentication for testing')
    parser.add_argument('--user', type=str, default='culurciello',
                        help='Username to use when bypassing auth (default: culurciello)')
    parser.add_argument('--port', type=int, default=3000,
                        help='Port to run the application on (default: 3000)')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    return parser.parse_args()

# Parse arguments
args = parse_args()

# Apache2 Configuration for https://geocoolee.com/mynewpage/
#
# Environment variables needed on server:
# export URL_PREFIX="/mynewpage"
# export APPLICATION_ROOT="/mynewpage/"
# export FLASK_ENV="production"
#
# Apache Virtual Host configuration needed:
# <VirtualHost *:443>
#     ServerName geocoolee.com
#     WSGIScriptAlias /mynewpage /home/euge/Public/mynewpage/app.wsgi
#     <Directory /home/euge/Public/mynewpage>
#         WSGIApplicationGroup %{GLOBAL}
#         Require all granted
#     </Directory>
# </VirtualHost>

# Create Flask app with static URL path configuration for subpage deployment
url_prefix = os.environ.get('URL_PREFIX', None)
if url_prefix:
    app = Flask(__name__, static_url_path=f'{url_prefix}/static')
else:
    app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///orb.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Testing and debugging configuration
app.config['BYPASS_AUTH'] = args.bypass_auth or os.environ.get('BYPASS_AUTH', 'false').lower() == 'true'
app.config['DEFAULT_TEST_USER'] = args.user if args.bypass_auth else os.environ.get('DEFAULT_TEST_USER', 'testuser')
app.config['DEFAULT_TEST_USER_ID'] = int(os.environ.get('DEFAULT_TEST_USER_ID', '1'))

# Configure for subpage deployment
# Set APPLICATION_ROOT to support deployment in subdirectories
app.config['APPLICATION_ROOT'] = os.environ.get('APPLICATION_ROOT', '/')

# Initialize extensions
db.init_app(app)
CORS(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Register routes blueprint with URL prefix support
from routes import bp
# For local testing, you can comment out the next line to disable URL prefix:
app.register_blueprint(bp, url_prefix=url_prefix)
# For local testing without prefix, uncomment this line instead:
# app.register_blueprint(bp)

def create_user_if_not_exists(username, email, full_name, password='password'):
    """Create a user if it doesn't exist."""
    from models import User, UserProfile

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(
            username=username,
            email=email,
            full_name=full_name
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create user profile
        profile = UserProfile(
            user_id=user.id,
            name=full_name.split()[0] if full_name else username,
            lastname=' '.join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else '',
            email=email
        )
        db.session.add(profile)
        db.session.commit()
        print(f"✅ Created user: {username}")
    else:
        print(f"✅ User exists: {username}")

    return user

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # If bypass auth is enabled, ensure the specified user exists
        if app.config['BYPASS_AUTH']:
            username = app.config['DEFAULT_TEST_USER']
            email = f"{username}@example.com"
            full_name = username.replace('_', ' ').title()
            user = create_user_if_not_exists(username, email, full_name)
            app.config['DEFAULT_TEST_USER_ID'] = user.id

            logger.info(f"🚀 Starting TheOrb in bypass mode")
            logger.info(f"👤 Using user: {username} (ID: {user.id})")
            logger.info(f"🌐 Access directly at: http://localhost:{args.port}/")
            print(f"🚀 Starting TheOrb in bypass mode")
            print(f"👤 Using user: {username} (ID: {user.id})")
            print(f"🌐 Access directly at: http://localhost:{args.port}/")
        else:
            logger.info(f"🚀 Starting TheOrb with authentication")
            logger.info(f"🌐 Login at: http://localhost:{args.port}/login")
            print(f"🚀 Starting TheOrb with authentication")
            print(f"🌐 Login at: http://localhost:{args.port}/login")

    app.run(debug=args.debug, host='0.0.0.0', port=args.port)