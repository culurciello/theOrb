#!/usr/bin/python3
import sys
import os

# Add your project directory to sys.path
sys.path.insert(0, "/path/to/theOrb-web/")

# Set environment variables for subpage deployment
os.environ['URL_PREFIX'] = '/mynewpage'
os.environ['APPLICATION_ROOT'] = '/mynewpage/'
os.environ['FLASK_ENV'] = 'production'

from app import app as application

if __name__ == "__main__":
    application.run()