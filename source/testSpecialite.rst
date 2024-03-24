Documentation for 'testSpecialite' Function
===========================================

This documentation provides information about the 'testSpecialite' function in the 'app.py' module.

Functionality
-------------

The 'testSpecialite' function serves as the endpoint for testing if a medication is a specialty. It handles POST requests.

Parameters
----------

- **medTest** (str): The medication to be tested.

Return Value
------------

This function returns the result of the `isSpecialite()` function, indicating whether the medication is a specialty.

Routes
------

- **/testSpecialite**: Endpoint for testing if a medication is a specialty.

Interaction with Database
-------------------------

- Calls the `isSpecialite()` function to check if the medication is a specialty.

This function provides a way to test if a medication is a specialty and returns the result accordingly.
