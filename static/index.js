
function dispose_result(){
    var element = document.getElementById("third");
    element.classList.toggle("invisible");
    element.style.display = 'none'
}

function clear_border(){
  input_Med.classList.remove("danger")
  input_Med.classList.remove("warning")
  input_Med.classList.remove("valide")
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
    formdata.append("medTest", substance);
    
    var requestOptions = {
      method: 'POST',
      body: formdata,
      redirect: 'follow'
    };
    
    const response = await fetch("http://127.0.0.1:5000/getListClasses", requestOptions)
      .then(response => response.text());

    return response
}

async function check_medicament(input_number){
    var input_Med = document.getElementById("med-"+input_number);
    var result = []
    var testCls = await testClasse(input_Med.value)
    var testSub = await testSubstance(input_Med.value)
    
    if(input_Med.value == "" || (testCls == "false" && testSub == "false")){
        input_Med.classList.add("danger")
        input_Med.classList.remove("warning")
        input_Med.classList.remove("valide")

        result = []
    // }else{
    //     if (input_Med.value == "SUB"){
    //         input_Med.classList.remove("danger")
    //         input_Med.classList.add("warning")
    //         input_Med.classList.remove("valide")       

    //         result.push("des classes")
    //     }else{
    //         input_Med.classList.remove("danger")
    //         input_Med.classList.remove("warning")
    //         input_Med.classList.add("valide") 

    //         result.push("une classe")
    //     }
    }

    console.log(result)
}