"""
Application entry point.

This module creates the Flask application instance using the factory pattern.
The variable is named 'application' for AWS Elastic Beanstalk compatibility.
"""
import os

# Configuration comes from the environment only: Doppler injects it locally
# (`doppler run -- python application.py`) and Railway in production.
from app import create_app

# Create the application instance
# Named 'application' for AWS Elastic Beanstalk compatibility
application = create_app()

if __name__ == "__main__":
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    application.run(debug=debug)
