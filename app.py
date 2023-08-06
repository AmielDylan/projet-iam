from flask import Flask, render_template, request, jsonify
from static.requetes import *
import os

 # create and configure the app
application = Flask(__name__, instance_relative_config=True)
application.config.from_mapping(SECRET_KEY='dev',)

# ensure the instance folder exists
try:
    os.makedirs(application.instance_path)
except OSError:
    pass

@application.route("/", methods =["GET", "POST"])
def home():
    # Resultat de la requete
    result = class_list_1 = class_list_2 = []
    temp = []
    args = []

    if request.method == "POST":
        # getting input with name = med-1 in HTML form
        med_1 = request.form.get("med-1")
        # getting input with name = med-2 in HTML form
        med_2 = request.form.get("med-2")

        interactions_med = getInteractionsMed(med_1=med_1.upper(), med_2=med_2.upper())
        temp.append(interactions_med[0])
        args.append(interactions_med[1])

        result = getFullResult(
            listRes=temp,args=args,
            med_1=med_1,
            med_2=med_2)

    return render_template('index.html', resultats = result, class_list_1 = class_list_1, class_list_2 = class_list_2)

@application.route('/testClasse', methods=['POST'])
def testClasse():
    medicament = request.form.get("medTest")
    return isClasse(medicament=medicament)

@application.route('/testSubstance', methods=['POST'])
def testSubstance():
    medicament = request.form.get("medTest")
    return isSubstance(medicament=medicament)

@application.route('/testSpecialite', methods=['POST'])
def testSpecialite():
    medicament = request.form.get("medTest")
    return isSpecialite(medicament=medicament)

@application.route('/getListClasses', methods=['POST'])
def getListClasses():
    resultat = []
    substance = request.form.get("substance")
    listId = getClassesIdFromSubstance(substance=substance)

    for value in listId:
        resultat.append(getClasseName(value))

    return resultat

@application.route('/autocomplete_input', methods=['POST'])
def autocomplete_input():
    # Récupérer la valeur de recherche depuis les paramètres de requête
    search_query = request.form.get("query")
    resultat = jsonify(autocomplete_data(search_query))

    return resultat


if __name__ == "__main__":
    application.run(debug=True)


