function selectElement(id, valueToSelect) {    
    let element = document.getElementById(id);
    element.value = valueToSelect;
}

let num = 0;
function addNewFeatureContainer(colname="", operator="", value="", nas=false) {
    const newFeatureContainer = document.createElement("div");

    checked = ""
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
                <input id="featurepos`+num+`" type="featurepos`+num+`" class="form-control" value="`+value+`">
            </div>
        </div>
        <div class="row">
            <div class="col-4" style="display: flex; align-items:center;">
                <label for="includeNA`+num+`" class="col-form-label">Include N/As</label>
            </div>
            <div class="col-8" style="display: flex; align-items:center;">
                <input id="includeNA`+num+`" class="paramNA" type="checkbox" `+checked+`>
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
    const pathHeader = document.getElementById('path');
    const path = '/'+pathHeader.innerText;
    console.log(features);

    $.ajax({
        type: 'POST',
        url: '/filesearchbegin',
        data: JSON.stringify({
            params: features,
            path: path
        }),
        contentType: 'application/json',
        success: function (response) {
            url = "/filesearch/preview";
            window.location.href = url;
        },
        error: function (error) {
            
        }
    });
}

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