window.onload = function(){
    var med_1 = document.getElementById("choix-classe-1");
    var med_2 = document.getElementById("choix-classe-2");

    med_1.style.display = 'none'
    med_2.style.display = 'none'
}

function dispose_result() {
    var element = document.getElementById("third");
    element.classList.toggle("invisible");
    element.style.display = 'none'
}