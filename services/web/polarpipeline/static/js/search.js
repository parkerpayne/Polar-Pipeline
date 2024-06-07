function storeCurrentParams(){
    const featurecontainer = document.getElementById("featureContainer");
    const featureitems = featurecontainer.children;
    const features = []
    for (let i = 0; i < featureitems.length; i++) {
        const featureitem = featureitems[i];
        const textFields = featureitems[i].querySelectorAll('.form-control');
        const dropdown = featureitems[i].querySelector('.form-select');
        const nas = featureitems[i].querySelector('.paramNA');
        const featurevals = []
        for (let j = 0; j < textFields.length; j++) {
            featurevals.push(textFields[j].value);
        }
        try{
            featurevals.push(dropdown.value)
            featurevals.push(nas.checked)
            features.push(featurevals);
        }catch{

        }
        
    }
    localStorage.setItem('parameters', JSON.stringify(features));
}

function retrieveCurrentParams(){
    const parameters = JSON.parse(localStorage.getItem('parameters'));
    
    if(!parameters){
        addNewFeatureContainer();
        return
    }else{
        parameters.forEach(element => {
            addNewFeatureContainer(element[0], element[2], element[1], element[3])
        });
    }
}

function selectElement(id, valueToSelect) {    
    let element = document.getElementById(id);
    element.value = valueToSelect;
}

let num = 0;
function addNewFeatureContainer(colname="", operator="", value="", nas=false) {
    const newFeatureContainer = document.createElement("div");

    let checked = ""
    if(nas){
        checked = "checked"
    }

    num++;
    newFeatureContainer.innerHTML = `
    <div class="param-container" id="feature`+num+`">
        <div class="row">
            <div class="col-4" style="display: flex; align-items:center;">
                <label for="featurename`+num+`" class="col-form-label">Column Name</label>
            </div>
            <div class="col-8" style="display: flex; align-items:center;">
                <input type="featurename`+num+`" class="form-control" list="columns" value="`+colname+`"">
            </div>
        </div>
        <div class="row">
            <div class="col-4" style="display: flex; align-items:center;">
                <label for="featurename`+num+`" class="col-form-label">Operator</label>
            </div>
            <div class="col-8" style="display: flex; align-items:center;">
                <select class="form-select btn btn-secondary dropdown-toggle" id="comparisonSelector`+num+`" style="min-width:100%" aria-label="Default select example" value="`+operator+`">
                    <option value>- Select -</option>
                    <option value="==">==</option>
                    <option value=">=">>=</option>
                    <option value="<="><=</option>
                    <option value=">">></option>
                    <option value="<"><</option>
                    <option value="!=">!=</option>
                    <option value="Contains">Contains</option>
                </select>
            </div>
        </div>
        <div class="row">
            <div class="col-4" style="display: flex; align-items:center;">
                <label for="featurepos`+num+`" class="col-form-label">Value</label>
            </div>
            <div class="col-8" style="display: flex; align-items:center;">
                <input type="featurepos`+num+`" class="form-control" value="`+value+`">
            </div>
        </div>
        <div class="row">
            <div class="col-4" style="display: flex; align-items:center;">
                <label for="includeNA`+num+`" class="col-form-label">Include N/As</label>
            </div>
            <div class="col-8" style="display: flex; align-items:center;">
                <input class="paramNA" type="checkbox" `+checked+`>
            </div>
        </div>
    </div>
    <span class="btn btn-light" id="deletefeature`+num+`" value="`+num+`" onclick="deleteFeature(this.getAttribute('value'))">Delete Parameter</span>
    `
    const featureContainer = document.getElementById("featureContainer");
    featureContainer.appendChild(newFeatureContainer);
    selectElement("comparisonSelector"+num, operator);
}
function deleteFeature(num) {
    const featureToRemove = document.getElementById('feature'+num);
    const buttonToRemove = document.getElementById('deletefeature'+num);
    buttonToRemove.remove()
    featureToRemove.remove()
}
function submitSearch(){
    check_progress();
    const pbar = document.getElementById("progressbar");
    if(pbar.classList.contains("bg-danger")){
        pbar.classList.remove("bg-danger");
    }
    if(pbar.classList.contains("bg-success")){
        pbar.classList.remove("bg-success");
    }
    if(pbar.classList.contains("bg-warning")){
        pbar.classList.remove("bg-warning");
    }
    const featurecontainer = document.getElementById("featureContainer");
    const featureitems = featurecontainer.children;
    const features = []
    for (let i = 0; i < featureitems.length; i++) {
        const featureitem = featureitems[i];
        const textFields = featureitems[i].querySelectorAll('.form-control');
        const dropdown = featureitems[i].querySelector('.form-select');
        const nas = featureitems[i].querySelector('.paramNA');
        const featurevals = []
        for (let j = 0; j < textFields.length; j++) {
            featurevals.push(textFields[j].value);
        }
        try{
            featurevals.push(dropdown.value)
            featurevals.push(nas.checked)
            features.push(featurevals);
        }catch{

        }
        
    }
    checkboxes = document.querySelectorAll('.cheqbox')
    const toSearch = []
    for (let i = 0; i < checkboxes.length; i++){
        if (checkboxes[i].checked){
            toSearch.push(checkboxes[i].value)
        }
    }
    console.log(features);
    console.log(toSearch);
    $.ajax({
        type: 'POST',
        url: '/beginsearch',
        data: JSON.stringify({
            params: features,
            files: toSearch
        }),
        contentType: 'application/json',
        success: function (response) {
            if(response == 'success'){
                const numsperpage = document.getElementById('numsperpageinput').value;
                window.location.href = url = "/search/"+numsperpage+"/0#Preview";
            }
        },
        error: function (error) {
            if (error.responseJSON.error == "empty"){
                alert("There is an unconfigured parameter. Please review and try again.")
            }else if(error.responseJSON.error == "no files"){
                alert("No files selected. Please select one and try again.")
            }else{
                if(!pbar.classList.contains("bg-danger")){
                    pbar.classList.add("bg-danger");
                }
            }
        }
    });
}
function cancelSearch(){
    $.ajax({
        type: 'GET',
        url: '/searchcancelled',
        contentType: 'application/json',
        success: function (response) {
            console.log(response);
        },
        error: function (error) {
            
        }
    });
}
var progressBar = document.getElementById('progressbar');
var timebtn = document.getElementById('timebtn');
var lastProgress = null;
var formattedTime = "--:--";
function check_progress() {
    fetch('/searchprogress')
        .then(response => response.json())
        .then(progress => {
            if (!lastProgress || JSON.stringify(progress) !== JSON.stringify(lastProgress)) {
                // Update the progress and formatted time if there's a change in progress
                lastProgress = progress;
                formattedTime = progress.remaining.minutes.toString().padStart(2, '0') + ":" + progress.remaining.seconds.toString().padStart(2, '0');
            } else {
                if (formattedTime !== "--:--") {
                    let [minutes, seconds] = formattedTime.split(':').map(Number);
                    if (seconds === 0) {
                        if (minutes === 0) {
                            return;
                        }
                        minutes -= 1;
                        seconds = 59;
                    } else {
                        seconds -= 1;
                    }
                    formattedTime = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                }
            }
            console.log(progress);
            progressBar.style.width = (progress.progress * 100).toFixed(0) + "%";
            progressBar.setAttribute('aria-valuenow', progress.progress);
            progressBar.innerText = (progress.progress * 100).toFixed(0) + "%";
            timebtn.innerText = "Remaining: " + formattedTime
            console.log("Remaining: " + formattedTime);
            if(progress.progress == 1){
                $('#cancelSearch').hide();
            }else{
                $('#cancelSearch').show();
            }
            if(progressBar.classList.contains("bg-success")){
                progressBar.classList.remove("bg-success");
            }
            if(progressBar.classList.contains("bg-warning")){
                progressBar.classList.remove("bg-warning");
            }
            if(progressBar.classList.contains("bg-danger")){
                progressBar.classList.remove("bg-danger");
            }
            if(progress.color == "green"){
                progressBar.classList.add("bg-success");
            }
            if(progress.color == "yellow"){
                progressBar.classList.add("bg-warning");
            }
            if(progress.color == "red"){
                progressBar.classList.add("bg-danger");
            }
            if(progressBar.classList.contains("progress-bar-animated") && progress.color != "spin"){
                progressBar.classList.remove("progress-bar-striped");
                progressBar.classList.remove("progress-bar-animated");
            }else if(!progressBar.classList.contains("progress-bar-animated") && progress.color == "spin"){
                progressBar.classList.add("progress-bar-striped");
                progressBar.classList.add("progress-bar-animated");
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    setTimeout(check_progress, 1000);
}
fetch('/searchprogress')
    .then(response => response.json())
    .then(progress => {
        console.log(progress);

        // Show or hide progress container based on progress value
        if (progress.progress !== 1) {
            check_progress();
        }else{
            $('#cancelSearch').hide();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });


function selection(instruction) {
    const checkboxes = document.querySelectorAll('.cheqbox');
    checkboxes.forEach(element => {
        if (instruction === "select") {
            element.checked = true;
        } else {
            element.checked = false;
        }
    });
}
function pagenumupdated(e){
    if((e && e.keyCode == 13) || e == 0) {
        generatePage(0);
    }
}
function generatePage(pagenum){
    const numsperpageinput = document.getElementById('numsperpageinput');
    numsperpage = 0
    if (numsperpageinput.value){
        // console.log(numsperpageinput.value);
        numsperpage = numsperpageinput.value;
    }else{
        // console.log(numsperpageinput.getAttribute('placeholder'))
        numsperpage = numsperpageinput.getAttribute('placeholder');
    }
    url = "/search/"+numsperpage+"/"+pagenum+"#Preview";
    window.location.href = url;
}
function nextPrevButtonClicked(){
    window.scrollTo(0, document.body.scrollHeight);
}
function download(){
    url = "/search/download";
    window.location.href = url;
    // const omitboxes = document.querySelectorAll('.omitbox');
    // omissions = [];
    // omitboxes.forEach(element => {
    //     if(element.checked){
    //         omissions.push(element.value);
    //     }
    // });
    // console.log(omissions);
    // $.ajax({
    //     type: 'POST',
    //     url: '/searchdownload',
    //     data: JSON.stringify({
    //         omissions: omissions
    //     }),
    //     contentType: 'application/json',
    //     success: function (response) {
    //         url = "/search/download";
    //         window.location.href = url;
    //     },
    //     error: function (error) {
    //         url = "/search/download";
    //         window.location.href = url;
    //     }
    // });
}