Documentation for 'testClasse' Function
========================================

This documentation provides information about the 'testClasse' function in the 'app.py' module.

Functionality
-------------

The 'testClasse' function serves as the endpoint for testing if a medication belongs to a specific class. It handles POST requests.

Parameters
----------

- **medTest** (str): The medication to be tested.

Return Value
------------

This function returns the result of the `isClasse()` function, indicating whether the medication belongs to the specified class.

Routes
------

- **/testClasse**: Endpoint for testing if a medication belongs to a specific class.

Interaction with Database
-------------------------

- Calls the `isClasse()` function to check if the medication belongs to a specific class.

This function provides a way to test if a medication belongs to a specific class and returns the result accordingly.
