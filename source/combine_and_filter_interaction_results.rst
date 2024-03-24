Function to combine and filter interaction results
==================================================

This function combines and filters interaction results retrieved from the database based on the provided lists of interaction results, medication class pairs, and medication names. It refines the raw interaction data to generate a more structured and user-friendly output.

Parameters:
-----------

- **listRes**: A list containing interaction results between two medications. Each interaction result is represented as a list with the following elements:
  - Index 0: Name of the first medication involved in the interaction.
  - Index 1: Name of the second medication involved in the interaction.
  - Index 2: ID of the interaction level.
  - Index 3: Description of the interaction.

- **args**: A list containing pairs of medication classes used to query interactions from the database. Each pair is represented as a list containing the medication classes associated with each medication.

- **med_1**: The name of the first medication.
- **med_2**: The name of the second medication.

Return Value:
-------------

- Returns a list containing filtered interaction results along with medication names. Each element of the list represents an interaction result and is structured as follows:
  - Index 0: Name of the first medication involved in the interaction.
  - Index 1: Name of the second medication involved in the interaction.
  - Index 2: Level of the interaction.
  - Index 3: Description of the interaction.

Exceptions:
-----------

- None

Note:
-----

This function is designed to be used internally to process raw interaction results before presenting them to the user. It ensures that only relevant and meaningful information is included in the final output.
