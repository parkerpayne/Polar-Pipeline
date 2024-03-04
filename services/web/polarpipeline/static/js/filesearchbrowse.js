

// function to copy path to clipboard when clicked on
function copyToClipboard(text) {
    var textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
}
// Function to open the file options modal
function openFileOptionsModal(fileName, filepath) {
    const fileinput = document.getElementById("filepath");
    fileinput.value = filepath
    window.location.href = url = "/filesearch/"+filepath;
}

function closeFileOptionsModal() {
    $('#fileOptionsModal').modal('hide');
    const notification = document.getElementById("notification");
    notification.style.opacity = "1";
    setTimeout(function () {
        notification.style.opacity = "0";
    }, 3000);// 3000 milliseconds (3 seconds)
}

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
                <input type="featurepos`+num+`" class="form-control" value="`+value+`">
            </div>
        </div>
        <div class="row">
            <div class="col-4" style="display: flex; align-items:center;">
                <label for="includeNA`+num+`" class="col-form-label">Include N/As</label>
            </div>
            <div class="col-8" style="display: flex; align-items:center;">
                <input class="paramNA" type="checkbox" value={{ db }} `+checked+`>
            </div>
        </div>
    </div>
    <span class="btn btn-light" id="deletefeature`+num+`" value="`+num+`" onclick="deleteFeature(this.getAttribute('value'))">Delete Parameter</span>
    `
    const featureContainer = document.getElementById("featureContainer");
    featureContainer.appendChild(newFeatureContainer);
    selectElement("comparisonSelector"+num, operator);
}