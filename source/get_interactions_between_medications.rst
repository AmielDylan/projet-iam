Function to retrieve interactions between two medications
==========================================================

This function is used to retrieve interactions between two medications based on their names.

Parameters:
-----------

- **med_1**: The name of the first medication.
- **med_2**: The name of the second medication.

Return Value:
-------------

- Returns a tuple containing:
  - A list of interaction results between the two medications. Each element of the list represents an interaction result and is structured as follows:
    - Index 0: Name of the first medication involved in the interaction.
    - Index 1: Name of the second medication involved in the interaction.
    - Index 2: Type of interaction (e.g., "Major", "Moderate", "Minor").
    - Index 3: Description of the interaction.
  - A list of tuples, where each tuple contains the pair of medication classes used to query interactions from the database.

Interaction Results:
--------------------

The interaction results returned by this function provide detailed information about interactions between the two medications. Each interaction result includes the names of the medications involved, the type of interaction, and a description of the interaction.

Medication Class Pairs:
------------------------

This function queries interaction results based on pairs of medication classes. The list of tuples returned alongside the interaction results contains pairs of medication classes used in the database query. These medication class pairs are essential for understanding the context of the interactions.

Interaction Query Process:
--------------------------

The function first identifies the classes of medications associated with each input medication. It then retrieves the substances and specialties related to these medications. For each medication, it determines whether it is a specialty, a class, or a substance and performs the necessary database queries to obtain the relevant information. Once the classes of medications associated with both input medications are identified, the function queries the database to retrieve interaction results based on pairs of medication classes.

Exceptions:
-----------

- Raises any error encountered during the database operation.

Note:
-----

Ensure that the database connection is properly established before calling this function.

