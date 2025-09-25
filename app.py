from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

from database import db

load_dotenv()

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

# Configure for subpage deployment
# Set APPLICATION_ROOT to support deployment in subdirectories
app.config['APPLICATION_ROOT'] = os.environ.get('APPLICATION_ROOT', '/')

# Initialize extensions
db.init_app(app)
CORS(app)

# Register routes blueprint with URL prefix support
from routes import bp
# For local testing, you can comment out the next line to disable URL prefix:
app.register_blueprint(bp, url_prefix=url_prefix)
# For local testing without prefix, uncomment this line instead:
# app.register_blueprint(bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0', port=3000)