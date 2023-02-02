import mysql.connector
from mysql.connector import errorcode, Error

# CONFIGURATIONS
config = {
  'user': 'root',
  'password': 'root',
  'host': '127.0.0.1',
  'database': 'projet_ipa',
  'raise_on_warnings': True
}

def connectToDB():
  try:
    cnx = mysql.connector.connect(**config)

  except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
      print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
      print("Database does not exist")
    else:
      print(err)
  else:
    return cnx

  finally:
    return cnx

# FONCTIONS
def isClasse(medicament):
  result = []

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    requete = 'SELECT projet_ipa.isClasse(%s)'
    value = (medicament,)
    cursor.execute(requete, value)
    result = cursor.fetchone()[0]
    cursor.close()

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result

def isSubstance(medicament):
  result = []

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    requete = 'SELECT projet_ipa.isSubstance(%s)'
    value = (medicament,)
    cursor.execute(requete, value)
    result = cursor.fetchone()[0]
    cursor.close()

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result

# PROCEDURES
def getClasse(idClasse):
  result = []

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [idClasse,0]
    
    result = cursor.callproc('getClasse', args)

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result[1] if len(result) > 0 else result

def getClassesId(substance):
  fetch = result = []
  
  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [substance]
    cursor.callproc('getClassesId', args)

    for value in cursor.stored_results():
      fetch = value.fetchall()
    
    for value in fetch:
      result.append(value[0])

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result

def getInteractionsMed(med_1, med_2):
  fetch = result = []

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [med_1, med_2]
    cursor.callproc('getInteractionsMed', args)

    for value in cursor.stored_results():
      fetch = value.fetchall()
    
    for value in fetch:
      result.append(value[1].strip('()'))
      result.append(value[3].strip('()'))
      result.append(value[4])
      result.append(value[5].strip('()'))
  except Error as err:
    print(err)
  else:
    cnx.close() 

  return result

def getNiveau(idNiveau):
  result = []

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [idNiveau,0]
    
    result = cursor.callproc('getNiveau', args)
  except Error as err:
    print(err)
  else:
    cnx.close() 

  return result[1] if len(result) > 0 else result

def getFullResult(res, med_1, med_2):
  if len(res) > 0:
    niveau = getNiveau(res[2])
    res[2] = niveau
    res.append(med_1)
    res.append(med_2)
    return res
  else:
    return []

print(getClassesId('ADRENALINE'))
