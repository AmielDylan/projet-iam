Documentation for 'home' Function
==================================

This documentation provides detailed information about the 'home' function in the 'app.py' module.

Functionality
-------------

The 'home' function serves as the endpoint for the home page of the interaction medicamenteuse web application. It handles both GET and POST requests.

Parameters
----------

- **med_1** (str): The first medication entered by the user.
- **med_2** (str): The second medication entered by the user.

Return Value
------------

This function renders the 'index.html' template with the interaction results and other data required for the home page.

Routes
------

- **/**: Endpoint for the home page.

HTML Template
-------------

- **index.html**: Template for the home page, where users can input medications and view interaction results.

Interaction Calculation
-----------------------

- Calls the `getInteractionsMed()` function to obtain interactions between the specified medications.
- Combines and filters interaction results using the `getFullResult()` function.

This function plays a central role in providing interaction information between medications and rendering the home page of the interaction medicamenteuse web application.
