Function to connect to the database
===================================

This function is used to establish a connection to the MySQL database using the specified configuration parameters.

.. code-block:: python

   def connectToDB():
       try:
           cnx = mysql.connector.connect(**config)
           return cnx

       except mysql.connector.Error as err:
           if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
               raise Exception("Something is wrong with your user name or password")
           elif err.errno == errorcode.ER_BAD_DB_ERROR:
               raise Exception("Database does not exist")
           else:
               raise err

Parameters:
-----------

This function takes no input parameters.

Return Value:
-------------

The function returns a MySQL connection object (`mysql.connector.connection.MySQLConnection`) if the connection is successful.

Exceptions:
-----------

- The `Exception` exception is raised if an error occurs during the database connection. Specific errors are handl
