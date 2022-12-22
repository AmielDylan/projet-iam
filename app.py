from flask import Flask, render_template, request
from requetes import *

app = Flask(__name__)

@app.route("/", methods =["GET", "POST"])
def home():
    # Resultat de la requete
    result = []

    if request.method == "POST":
        # getting input with name = med-1 in HTML form
        med_1 = request.form.get("med-1")
        # getting input with name = med-2 in HTML form
        med_2 = request.form.get("med-2")
    
        result = getFullResult(
            getInteractionsMed(med_1=med_1.upper(), med_2=med_2.upper()),
            med_1=med_1,
            med_2=med_2)

    return render_template('index.html', resultat = result)

# start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)