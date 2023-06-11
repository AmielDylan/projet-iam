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

def isSpecialite(medicament):
  result = []

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    requete = 'SELECT projet_ipa.isSpecialite(%s)'
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

def getSubstanceId(specialite):
  fetch = result = []
  
  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [specialite]
    cursor.callproc('getSubstanceId', args)

    for value in cursor.stored_results():
      fetch = value.fetchall()
    
    for value in fetch:
      result.append(value[0])

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result

def getSubstanceName(idSubstance):
  result = []

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    args = [idSubstance,0]

    result = cursor.callproc('getSubstanceName', args)

  except Error as err:
      print(err)
  else:
    cnx.close()

  return result[1] if len(result) > 0 else result

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
  """ If med 1 is a specialite : """
  if eval(isSpecialite(med_1)):
    listSubstancesId = getSubstanceId(med_1)
    for value in listSubstancesId:
      res = getClassesIdFromSubstance(getSubstanceName(value))
      listClasses_1.append(res[0])
      # [i.append(a) for i,a in zip(listClasses_1, getClassesIdFromSubstance(getSubstanceName(value)))]

  """ If med 1 is a substance : """
  if eval(isSubstance(med_1)):
    listClasses_1 = getClassesIdFromSubstance(med_1)
  
  """ If med 1 is a classe : """
  if eval(isClasse(med_1)):
    listClasses_1.append(getClasseId(med_1)[0])

  # Classes id from med 2
  """ If med 2 is a specialite : """
  if eval(isSpecialite(med_2)):
    listSubstancesId_2 = getSubstanceId(med_2)
    for value in listSubstancesId_2:
      res = getClassesIdFromSubstance(getSubstanceName(value))
      listClasses_2.append(res[0])
      # [i.append(a) for i,a in zip(listClasses_2,getClassesIdFromSubstance(value))]

  """ If med 2 is a substance : """
  if eval(isSubstance(med_2)):
    listClasses_2 = getClassesIdFromSubstance(med_2)
  
  """ If med 2 is a classe : """
  if eval(isClasse(med_2)):
    listClasses_2.append(getClasseId(med_2)[0])

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
          if len(fetch) == 0:
            fetch.append(None)
        
        for value in fetch:
          temp.append("None") if value is None else temp.append(value[0])

  except Error as err:
      print(err)
  else:
    cnx.close() 

  if len(temp) > 0:
    for value in temp:
      result.append(getInteractionsResults(value)) if value != "None" else result.append([None])

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

def getFullResult(listRes : list, args : list, med_1 : str, med_2 : str):
  # Flatten (kind of)
  listRes = listRes[0]
  args = args[0]

  # Comprehension de liste pour combiner les deux listes
  [i.append(a) for i,a in zip(args, listRes) if (type(i) is list)]

  # print(args)

  # Fonction lambda pour filtrer les éléments de list1
  filter_func = lambda x: [None] not in x

  # Filtrer les éléments de args
  resultat = list(filter(filter_func, args))

  # return resultat
  if len(resultat) > 0:
    for value in resultat:
      niveau = getNiveau(value[2][2])
      value[2][2] = niveau
    resultat.append(med_1)
    resultat.append(med_2)
    return resultat
  else:
    return []
  
# AUTOCOMPLETION
def autocomplete_data(search):
  result = []
  search_query = search
  limit = 6

  try:
    cnx = connectToDB()
    cursor = cnx.cursor()
    requete = """
          SELECT denomination AS resultat
          FROM projet_ipa.classes
          WHERE denomination LIKE %s
          UNION
          SELECT specialites AS resultat
          FROM projet_ipa.specialites
          WHERE specialites LIKE %s
          UNION
          SELECT substances AS resultat
          FROM projet_ipa.substances
          WHERE substances LIKE %s
          ORDER BY resultat ASC 
          LIMIT %s;
    """
    value = (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", limit)
    cursor.execute(requete, value)
    result = cursor.fetchall()
    cursor.close()

    # Créer une liste de résultats
    autocomplete_results = []
    for row in result:
        item = {
            'resultat': row[0],
        }
        autocomplete_results.append(item)

  except Error as err:
      print(err)
  else:
    cnx.close()

  # Retourner les résultats
  return autocomplete_results

getInteractionsMed("CIPROFLOXACINE", "TRAMADOL")