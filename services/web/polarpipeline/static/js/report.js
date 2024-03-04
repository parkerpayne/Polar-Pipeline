function submitToVep(){
    const inputBox = document.getElementById("inputBox");
    const inputVal = inputBox.value;
    var regex = /chr(\w+)_(\w+)_(\w+)\/(\w+)/;
    var result = inputVal.replace(regex, "$1:$2:$3:$4");
    url = "/report/"+result;
    window.location.href = url;
}