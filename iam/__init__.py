from flask import Flask, render_template, request, jsonify
from iam.requetes import *
import os

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/", methods =["GET", "POST"])
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

            temp.append(getInteractionsMed(med_1=med_1.upper(), med_2=med_2.upper())[0])
            args.append(getInteractionsMed(med_1=med_1.upper(), med_2=med_2.upper())[1])

            result = getFullResult(
                listRes=temp,args=args,
                med_1=med_1,
                med_2=med_2)

        return render_template('index.html', resultats = result, class_list_1 = class_list_1, class_list_2 = class_list_2)

    @app.route('/testClasse', methods=['POST'])
    def testClasse():
        medicament = request.form.get("medTest")
        return isClasse(medicament=medicament)

    @app.route('/testSubstance', methods=['POST'])
    def testSubstance():
        medicament = request.form.get("medTest")
        return isSubstance(medicament=medicament)
    
    @app.route('/testSpecialite', methods=['POST'])
    def testSpecialite():
        medicament = request.form.get("medTest")
        return isSpecialite(medicament=medicament)

    @app.route('/getListClasses', methods=['POST'])
    def getListClasses():
        resultat = []
        substance = request.form.get("substance")
        listId = getClassesIdFromSubstance(substance=substance)

        for value in listId:
            resultat.append(getClasseName(value))

        return resultat
    
    @app.route('/autocomplete_input', methods=['POST'])
    def autocomplete_input():
        # Récupérer la valeur de recherche depuis les paramètres de requête
        search_query = request.form.get("query")
        resultat = jsonify(autocomplete_data(search_query))

        return resultat

    return app
