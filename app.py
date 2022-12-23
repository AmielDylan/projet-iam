from flask import Flask, render_template, request
from requetes import *

app = Flask(__name__)

@app.route("/", methods =["GET", "POST"])
def home():
    # Resultat de la requete
    result = class_list_1 = class_list_2 = []

    if request.method == "POST":
        # getting input with name = med-1 in HTML form
        med_1 = request.form.get("med-1")
        # getting input with name = med-2 in HTML form
        med_2 = request.form.get("med-2")
    
        result = getFullResult(
            getInteractionsMed(med_1=med_1.upper(), med_2=med_2.upper()),
            med_1=med_1,
            med_2=med_2)

    return render_template('index.html', resultat = result, class_list_1 = class_list_1, class_list_2 = class_list_2)

@app.route('/testClasse', methods=['POST'])
def testClasse():
    medicament = request.form.get("medTest")
    return isClasse(medicament=medicament)

@app.route('/testSubstance', methods=['POST'])
def testSubstance():
    medicament = request.form.get("medTest")
    return isSubstance(medicament=medicament)

@app.route('/getListClasses', methods=['POST'])
def getListClasses():
    resultat = []
    substance = request.form.get("substance")
    listId = getClassesId(substance=substance)

    for value in listId:
        resultat.append(getClasse(value))

    return resultat


# start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)