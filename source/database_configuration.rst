Database Configuration
======================

The following configuration is used to connect to the MySQL database in the project:

.. code-block:: python

   config = {
     'user': 'root',
     'password': 'root',
     'host': '127.0.0.1',
     'database': 'projet_ipa',
     'raise_on_warnings': True
   }

Configuration Parameters
------------------------

- **user**: Username to connect to the MySQL database.
- **password**: Password associated with the user to connect to the MySQL database.
- **host**: IP address of the MySQL server.
- **database**: Name of the database to connect to.
- **raise_on_warnings**: Boolean indicating whether to raise an exception on warning.

``user``, ``password``, ``host``, and ``database`` are mandatory parameters, while ``raise_on_warnings`` is optional and defaults to True.

Note: Ensure that the database connection information is correct and secure.