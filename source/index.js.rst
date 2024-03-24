Documentation for index.js
===========================

This documentation provides an overview of the JavaScript functions in the 'index.js' file, which help manage the behavior of the HTML page.

Initialization and Event Listeners
----------------------------------

When the page loads, the 'window.onload' event triggers the initialization process. This event ensures that the necessary elements are prepared and event listeners are set up to handle user interactions effectively.

- **window.onload**: 
    - This event listener triggers the initialization process when the page finishes loading. Upon initialization, it sets up the necessary elements and event listeners for dynamic behavior.

Functionality and Behavior
---------------------------

The JavaScript functions in 'index.js' facilitate various aspects of the user interface, including autocomplete functionality, input validation, and result handling.

Autocomplete Functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~

The 'autocomplete' function retrieves suggestions based on the user's input and dynamically populates the autocomplete dropdown with matching results. It utilizes a POST request to the server to fetch suggestions and updates the dropdown accordingly.

Input Validation
~~~~~~~~~~~~~~~~

Input validation is crucial for ensuring data integrity and providing feedback to users about the validity of their input. The 'check_medicament' function performs validation checks on the entered medication and updates the input field's state accordingly. It distinguishes between valid, invalid, and potentially valid inputs and provides visual cues to the user.

Event Handling
~~~~~~~~~~~~~~

Event listeners are utilized to handle user interactions effectively and trigger appropriate actions based on user input. For example:
- Input events on medication input fields ('inputField.addEventListener') trigger the autocomplete function to fetch suggestions dynamically.
- Click events on autocomplete suggestions ('suggestion.addEventListener') update the input field with the selected suggestion and trigger further actions, such as medication validation and result retrieval.

Result Handling
~~~~~~~~~~~~~~~

Result handling involves managing the display of retrieved data and providing a clear presentation to the user. The 'replace_value' function updates the input field with the selected medication, while the 'dispose_result' function clears previously displayed results to make space for new ones.


Function Details
----------------

- **window.onload**: 
    - This function is triggered when the page is loaded. It initializes elements and event listeners for autocomplete functionality.

- **show_infos(input_number)**:
    - This function dynamically displays information based on the input number passed as an argument. It toggles the visibility of elements related to the specified input.

- **input_default(input_Med, input_number)**:
    - This function sets the default state for the input field with the specified number. It resets the input field to its initial state.

- **input_danger(input_Med, input_number)**:
    - This function sets the input field to a danger state if the entered value is invalid. It changes the input field's border color to red and updates the helper text to indicate an incorrect input.

- **input_warning(input_Med, input_number)**:
    - This function sets the input field to a warning state if the entered value requires attention. It changes the input field's border color to yellow and updates the helper text to provide additional information.

- **input_valid(input_Med, input_number)**:
    - This function sets the input field to a valid state if the entered value is correct. It changes the input field's border color to green and updates the helper text to indicate a valid input.

- **remove_infos(input_number)**:
    - This function removes displayed information related to the specified input number. It hides the details or suggestions related to the input.

- **dispose_result()**:
    - This function disposes of the result displayed on the page. It removes the result from the DOM to clear space for new results.

- **replace_value(value, input_number)**:
    - This function replaces the value of the input field with the specified value. It updates the input field's value with the selected suggestion.

- **clear_border(input_number)**:
    - This function clears the border of the input field. It removes any border color applied to the input field, restoring it to the default state.

- **append_classes(listClasses, input_number)**:
    - This function appends classes to the input field based on the provided list of classes. It populates the autocomplete dropdown with suggested class names based on the entered substance.

- **testClasse(medicament)**:
    - This function sends a POST request to the server to test if the given medication is a class.

- **testSubstance(medicament)**:
    - This function sends a POST request to the server to test if the given medication is a substance.

- **testSpecialite(medicament)**:
    - This function sends a POST request to the server to test if the given medication is a specialty.

- **getListClasses(substance)**:
    - This function sends a POST request to the server to retrieve a list of classes based on the provided substance.

- **check_medicament(input_number)**:
    - This function checks the medication entered in the input field and updates its state accordingly. It performs validation checks and displays relevant information based on the input.

- **autocomplete(input_number)**:
    - This function retrieves autocomplete suggestions based on the input value entered in the input field. It sends a POST request to the server to fetch suggestions matching the entered query.
