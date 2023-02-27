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

  return eval(result)

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

  return eval(result)

# PROCEDURES
def getClasseName(idClasse):
  result = []

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [idClasse,0]

    result = cursor.callproc('getClasseName', args)

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result[1] if len(result) > 0 else result

def getClassesIdFromSubstance(substance):
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

def getClasseId(className):
  fetch = result = []
  
  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [className]
    cursor.callproc('getClasseId', args)

    for value in cursor.stored_results():
      fetch = value.fetchall()
    
    for value in fetch:
      result.append(value[0])

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result

def getInteractionsResults(id):
  fetch = result = []
  
  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [id]
    cursor.callproc('getInteractionsResults', args)

    for value in cursor.stored_results():
      fetch = value.fetchall()
    
    for value in fetch:
      result.append(value[2].strip('()'))
      result.append(value[4].strip('()'))
      result.append(value[5])
      result.append(value[6].strip('()'))

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result

def getInteractionsMed(med_1, med_2):
  fetch, temp, result, listClasses_1, listClasses_2, listArgs = [],[],[],[],[],[]

  # Classes id from med 1
  if isSubstance(med_1):
    listClasses_1 = getClassesIdFromSubstance(med_1)
  elif isClasse(med_1):
    listClasses_1 = getClasseId(med_1)

  # Classes id from med 2
  if isSubstance(med_2):
    listClasses_2 = getClassesIdFromSubstance(med_2)
  elif isClasse(med_2):
    listClasses_2 = getClasseId(med_2)

  listClasses_1 = [getClasseName(id) for id in listClasses_1]
  listClasses_2 = [getClasseName(id) for id in listClasses_2]

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()

    for value1 in listClasses_1:
      for value2 in listClasses_2:
        args = [value1, value2]
        cursor.callproc('getInteractionsClasses', args)
        listArgs.append(args)

        for value in cursor.stored_results():
          fetch = value.fetchall()
        
        for value in fetch:
          temp.append(value[0])

  except Error as err:
      print(err)
  else:
    cnx.close() 

  if len(temp) > 0:
    for value in temp:
      result.append(getInteractionsResults(value))

  return result, listArgs

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

def getFullResult(listRes, args, med_1, med_2):
  # List Comprehension qui rajoute les classes à la suite de chaque interaction
  [i.append(a) for i,a in zip(listRes,args)]

  res=listRes

  if len(res) > 0:
    for value in res:
      niveau = getNiveau(value[2])
      value[2] = niveau
    res.append(med_1)
    res.append(med_2)
    return res
  else:
    return []
  
print(
  getFullResult(
    getInteractionsMed('abatacept'.upper(),'anti-tnf alpha'.upper())[0],
    getInteractionsMed('abatacept'.upper(),'anti-tnf alpha'.upper())[1],
    "",""))