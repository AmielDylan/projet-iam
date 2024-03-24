Documentation for 'app.py' Module
==================================

This module contains the main Flask application that serves as the backend for the interaction medicamenteuse web application.

Functionality
-------------

- Initializes the Flask application.
- Defines routes for handling HTTP requests.
- Interacts with the database using functions from the `requetes.py` module.

Dependencies
------------

- **Flask**: Web framework for building the backend of the application.
- **render_template**: Function for rendering HTML templates.
- **request**: Object for accessing request data in Flask.
- **jsonify**: Function for creating JSON responses in Flask.
- **static.requetes**: Module containing functions for interacting with the database.

Configuration
-------------

- **SECRET_KEY**: Secret key used for session management and other security-related features.

Routes
------

- :doc:`home`: Endpoint for the home page.
- :doc:`testClasse`: Endpoint for testing if a medication belongs to a specific class.
- :doc:`testSubstance`: Endpoint for testing if a medication is a substance.
- :doc:`testSpecialite`: Endpoint for testing if a medication is a specialty.
- :doc:`getListClasses`: Endpoint for retrieving a list of classes associated with a substance.
- :doc:`autocomplete_input`: Endpoint for providing autocomplete suggestions based on user input.

Function List
-------------

- :doc:`home`: Home Route Function
- :doc:`testClasse`: Test Classe Function
- :doc:`testSubstance`: Test Substance Function
- :doc:`testSpecialite`: Test Specialite Function
- :doc:`getListClasses`: Get List Classes Function
- :doc:`autocomplete_input`: Autocomplete Input Function

This file serves as the entry point for the interaction medicamenteuse web application and contains the necessary routes and configurations to handle HTTP requests and interact with the database.
