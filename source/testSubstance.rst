Documentation for 'testSubstance' Function
==========================================

This documentation provides information about the 'testSubstance' function in the 'app.py' module.

Functionality
-------------

The 'testSubstance' function serves as the endpoint for testing if a medication is a substance. It handles POST requests.

Parameters
----------

- **medTest** (str): The medication to be tested.

Return Value
------------

This function returns the result of the `isSubstance()` function, indicating whether the medication is a substance.

Routes
------

- **/testSubstance**: Endpoint for testing if a medication is a substance.

Interaction with Database
-------------------------

- Calls the `isSubstance()` function to check if the medication is a substance.

This function provides a way to test if a medication is a substance and returns the result accordingly.
