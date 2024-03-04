function submitToVep(){
    const inputBox = document.getElementById("inputBox");
    const inputVal = inputBox.value;
    var regex = /chr(\w+)_(\w+)_(\w+)\/(\w+)/;
    var result = inputVal.replace(regex, "$1:$2:$3:$4");
    var encodedResult = encodeURIComponent(result);
    url = "/frequency/"+encodedResult;
    window.location.href = url;
}

function notification(){
    var progressBar = document.getElementById('progressbar');
    var notificationValue = document.getElementById('notificationValue');
    var barColor = notificationValue.value;

    if (barColor == "green"){
        progressBar.classList.add("bg-success");
    }
}

function beginsearch(){
    var progressBar = document.getElementById('progressbar');
    progressBar.classList.remove("bg-success");
}