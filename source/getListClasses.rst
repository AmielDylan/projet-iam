Documentation for 'getListClasses' Function
===========================================

This documentation provides information about the 'getListClasses' function in the 'app.py' module.

Functionality
-------------

The 'getListClasses' function serves as the endpoint for retrieving a list of classes associated with a given substance. It handles POST requests.

Parameters
----------

- **substance** (str): The substance for which to retrieve the list of associated classes.

Return Value
------------

This function returns a list of class names associated with the specified substance.

Routes
------

- **/getListClasses**: Endpoint for retrieving a list of classes associated with a substance.

Interaction with Database
-------------------------

- Calls the `getClassesIdFromSubstance()` function to obtain the list of class IDs associated with the substance.
- Retrieves the class names using the `getClasseName()` function for each class ID.

This function provides a way to retrieve a list of classes associated with a substance and returns the result accordingly.
