
window.onload = function(){
  var details_1 = document.getElementById("choix-classe-1");
  var details_2 = document.getElementById("choix-classe-2");

  details_1.classList.add("invisible")
  details_2.classList.add("invisible")
}

function show_infos(input_number){
  var details = document.getElementById("choix-classe-"+input_number);
  details.classList.remove("invisible")
  details.classList.add("visible")
}

function input_default(input_Med, input_number){
  var helper = document.getElementById("med-"+input_number+"-helper")
  helper.innerText = "Evitez les charactères spéciaux svp."

  helper.classList.remove("text-danger")
  helper.classList.remove("text-success")
  helper.classList.remove("text-warning")
}

function input_danger(input_Med, input_number){
  var helper = document.getElementById("med-"+input_number+"-helper")

  input_Med.classList.add("danger")
  input_Med.classList.remove("warning")
  input_Med.classList.remove("valide")

  helper.innerText = "Entrez une valeur correcte svp."

  helper.classList.add("text-danger")
  helper.classList.remove("text-success")
  helper.classList.remove("text-warning")
}

function input_warning(input_Med, input_number){
  var helper = document.getElementById("med-"+input_number+"-helper")

  input_Med.classList.remove("danger")
  input_Med.classList.add("warning")
  input_Med.classList.remove("valide")

  helper.innerText = "Informations disponible"

  helper.classList.remove("text-danger")
  helper.classList.remove("text-success")
  helper.classList.add("text-warning")
}

function input_valid(input_Med, input_number){
  var helper = document.getElementById("med-"+input_number+"-helper")

  input_Med.classList.remove("danger")
  input_Med.classList.remove("warning")
  input_Med.classList.add("valide")

  helper.innerText = "Entrée valide"

  helper.classList.remove("text-danger")
  helper.classList.add("text-success")
  helper.classList.remove("text-warning")
}

function remove_infos(input_number){
  var details = document.getElementById("choix-classe-"+input_number);
  details.classList.add("invisible")
  details.classList.remove("visible")
}

function dispose_result(){
    var element = document.getElementById("third");

    if (element){
      element.classList.toggle("invisible");
      element.style.display = 'none'
    }

}

function replace_value(value, input_number){
  var input_Med = document.getElementById("med-"+input_number)
  input_Med.value = value

  remove_infos(input_number)
  check_medicament(input_number)
}

function clear_border(input_number){
  var input_Med = document.getElementById("med-"+input_number);
  input_Med.classList.remove("danger")
  input_Med.classList.remove("warning")
  input_Med.classList.remove("valide")
  remove_infos(input_number)
  input_default(input_Med, input_number)
}

function append_classes(listClasses, input_number){
  var listResponse = []
  var propositions = document.getElementById("propositions-"+input_number)

  while (propositions.hasChildNodes()) {
    propositions.removeChild(document.getElementById("propositions-"+input_number).firstChild);
  }

  listClasses.forEach(element => {
    const response = document.createElement("button")
    response.classList.add("btn", "btn-lg", "btn-warning", "rounded-pill")
    response.setAttribute("type", "button")
    response.setAttribute("onclick", "replace_value(\""+element+"\","+input_number+")")
    response.innerHTML = element
    listResponse.push(response)
  });

  listResponse.forEach(element => {
    var details = document.getElementById("propositions-"+input_number)
    details.appendChild(element)
  })
}

async function testClasse(medicament){
    var formdata = new FormData();
    formdata.append("medTest", medicament);
    
    var requestOptions = {
      method: 'POST',
      body: formdata,
      redirect: 'follow'
    };
    
    const response = await fetch("http://127.0.0.1:5000/testClasse", requestOptions)
      .then(response => response.text());

    return response
}

async function testSubstance(medicament){
    var formdata = new FormData();
    formdata.append("medTest", medicament);
    
    var requestOptions = {
      method: 'POST',
      body: formdata,
      redirect: 'follow'
    };
    
    const response = await fetch("http://127.0.0.1:5000/testSubstance", requestOptions)
      .then(response => response.text());

    return response
}

async function getListClasses(substance){
    var formdata = new FormData();
    formdata.append("substance", substance);
    
    var requestOptions = {
      method: 'POST',
      body: formdata,
      redirect: 'follow'
    };
    
    const response = await fetch("http://127.0.0.1:5000/getListClasses?pretty", requestOptions)
      .then(response => response.text());

    return JSON.parse(response)
}

async function check_medicament(input_number){
    var input_Med = document.getElementById("med-"+input_number);
    var result = []
    var testCls = await testClasse(input_Med.value)
    var testSub = await testSubstance(input_Med.value)    
    
    if(input_Med.value == "" || (testCls == "false" && testSub == "false")){
        input_danger(input_Med, input_number)
        remove_infos(input_number)

        result = []
    }else{
        if (testSub == "true"){ 
            input_warning(input_Med, input_number)
            show_infos(input_number)
            
            var listClasses = await getListClasses(input_Med.value)
            result.push(listClasses)

            append_classes(result[0], input_number)

        }else{
            input_valid(input_Med, input_number)
            remove_infos(input_number)

            result.push(input_Med.value)
        }
    }

    return result
}
