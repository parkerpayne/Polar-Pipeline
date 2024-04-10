function submitToVep(){
    const inputBox = document.getElementById("inputBox");
    const inputVal = inputBox.value;
    var regex = /chr(\w+)_(\w+)_(\w+)\/(\w+)/;
    var result = inputVal.replace(regex, "$1:$2:$3:$4");
    url = "/report/"+result;
    window.location.href = url;
}

function submitFileToVep(){
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const inputBox = document.getElementById('inputBox');
    const fileName = fileInput.files[0].name;
    // console.log('Selected file:', fileName);
    inputBox.placeholder = fileName;
    uploadForm.submit();
    check_progress();
    showProgressContainer();
}

function showProgressContainer() {
    $('#progressContainer').slideDown();
}

var progressBar = document.getElementById('progressbar');
function check_progress(){
    fetch('/report_progress')
        .then(response => response.json())
        .then(progress => {
            // console.log(progress);
            progressBar.style.width = (progress.progress * 100).toFixed(0) + "%";
            progressBar.setAttribute('aria-valuenow', progress.progress);
            progressBar.innerText = (progress.progress * 100).toFixed(0) + "%";
        })
        .catch(error => {
            console.error('Error:', error);
        });
    setTimeout(check_progress, 1000);
}