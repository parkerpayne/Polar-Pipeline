function saveInfo() {

    const presetname = document.getElementById("presetname").value;

    const protnamefield = document.getElementById("protname");
    const proteinname = protnamefield.value;

    const abprotnamefield = document.getElementById("abprotname");
    const abproteinname = abprotnamefield.value;

    const homoradio = document.getElementById('zygosity2');
    homo = homoradio.checked;
    console.log(homo);
    if (!homo){
        const leftstrucs = document.getElementById("leftstrucs");
        const leftitems = leftstrucs.children;
        const leftstructures = []
        for (let i = 0; i < leftitems.length; i++) {
            const leftitem = leftitems[i];
            const textFields = leftitems[i].querySelectorAll('.form-control');
            const strucvals = []
            for (let j = 0; j < textFields.length; j++) {
                strucvals.push(textFields[j].value);
            }
            leftstructures.push(strucvals);
        }
        
        const leftlenfield = document.getElementById("protlenleft");
        const leftlen = leftlenfield.value;

        let rightlen;
        let rightstructures;
        const same = document.getElementById("sameradio1").checked;
        if (same){
            rightlen = leftlen;
            rightstructures = leftstructures;
        }else{
            const rightstrucs = document.getElementById("rightstrucs");
            const rightitems = rightstrucs.children;
            rightstructures = []
            for (let i = 0; i < rightitems.length; i++) {
                const rightitem = rightitems[i];
                const textFields = rightitems[i].querySelectorAll('.form-control');
                const strucvals = []
                for (let j = 0; j < textFields.length; j++) {
                    strucvals.push(textFields[j].value);
                }
                rightstructures.push(strucvals);
            }
            const rightlenfield = document.getElementById("protlenright");
            rightlen = rightlenfield.value;
        }


        const leftfeaturecontainer = document.getElementById("featurecontainerleft");
        const leftfeatureitems = leftfeaturecontainer.children;
        const leftfeatures = []
        for (let i = 0; i < leftfeatureitems.length; i++) {
            const leftfeatureitem = leftfeatureitems[i];
            const textFields = leftfeatureitems[i].querySelectorAll('.form-control');
            const featurevals = []
            for (let j = 0; j < textFields.length; j++) {
                featurevals.push(textFields[j].value);
            }
            leftfeatures.push(featurevals);
        }
        const rightfeaturecontainer = document.getElementById("featurecontainerright");
        const rightfeatureitems = rightfeaturecontainer.children;
        const rightfeatures = []
        for (let i = 0; i < rightfeatureitems.length; i++) {
            const rightfeatureitem = rightfeatureitems[i];
            const textFields = rightfeatureitems[i].querySelectorAll('.form-control');
            const featurevals = []
            for (let j = 0; j < textFields.length; j++) {
                featurevals.push(textFields[j].value);
            }
            rightfeatures.push(featurevals);
        }

        console.log(homo)
        console.log(abproteinname);
        console.log(proteinname);
        console.log(leftlen);
        console.log(leftstructures);
        console.log(rightlen);
        console.log(rightstructures);
        console.log(leftfeatures);
        console.log(rightfeatures);

        $.ajax({
            type: 'POST',
            url: '/saveState',
            data: JSON.stringify({
                presetname: presetname,
                homo: homo,
                abproteinname: abproteinname,
                proteinname: proteinname,
                leftlen: leftlen,
                leftstructures: leftstructures,
                rightlen: rightlen,
                rightstructures: rightstructures,
                leftfeatures: leftfeatures,
                rightfeatures: rightfeatures
            }),
            contentType: 'application/json',
            success: function (response) {
                document.getElementById("resultcontainer").innerHTML += "";
            },
            error: function () {
                alert("Error. Are all fields correct?");
            }
        });
        
    }else{
        let homolen;
        let homostructures;
        const homostrucs = document.getElementById("homostrucs");
        const homoitems = homostrucs.children;
        homostructures = []
        for (let i = 0; i < homoitems.length; i++) {
            const homoitem = homoitems[i];
            const textFields = homoitems[i].querySelectorAll('.form-control');
            const strucvals = []
            for (let j = 0; j < textFields.length; j++) {
                strucvals.push(textFields[j].value);
            }
            homostructures.push(strucvals);
        }
        const homolenfield = document.getElementById("protlenhomo");
        homolen = homolenfield.value;

        const homofeaturecontainer = document.getElementById("featurecontainerhomo");
        const homofeatureitems = homofeaturecontainer.children;
        const homofeatures = []
        for (let i = 0; i < homofeatureitems.length; i++) {
            const homofeatureitem = homofeatureitems[i];
            const textFields = homofeatureitems[i].querySelectorAll('.form-control');
            const featurevals = []
            for (let j = 0; j < textFields.length; j++) {
                featurevals.push(textFields[j].value);
            }
            homofeatures.push(featurevals);
        }

        console.log(homo);
        console.log(abproteinname);
        console.log(proteinname);
        console.log(homolen);
        console.log(homostructures);
        console.log(homofeatures);
    
        $.ajax({
            type: 'POST',
            url: '/saveState',
            data: JSON.stringify({
                presetname: presetname,
                homo: homo,
                abproteinname: abproteinname,
                proteinname: proteinname,
                homolen: homolen,
                homostructures: homostructures,
                homolen: homolen,
                homofeatures: homofeatures,
            }),
            contentType: 'application/json',
            success: function (response) {
                document.getElementById("resultcontainer").innerHTML += "";
            },
            error: function () {
                alert("Error. Are all fields correct?");
            }
        });
    }

    }

    function loadStates(){
    $.ajax({
        type: 'POST',
        url: '/loadStates',
        data: JSON.stringify({
            empty: 'empty'
        }),
        contentType: 'application/json',
        success: function(response){
            const dropdown_ = document.getElementById('selectPreset');
            while (dropdown_.firstChild) {
                dropdown_.removeChild(dropdown_.firstChild);
            }
            response.data.forEach((preset) => {
                const newPresetOption = document.createElement("option");
                newPresetOption.className = "struc-container";
                newPresetOption.value = preset;
                newPresetOption.innerText = preset;
                dropdown_.appendChild(newPresetOption);
            });
        },
        error: function() {
            alert("Error. Could not load presets.");
        }
    })
    }

    function deepEqual(arr1, arr2) {
    if (arr1.length !== arr2.length) {
        return false;
    }

    for (let i = 0; i < arr1.length; i++) {
        if (Array.isArray(arr1[i]) && Array.isArray(arr2[i])) {
            if (!deepEqual(arr1[i], arr2[i])) {
                return false;
            }
        } else if (arr1[i] !== arr2[i]) {
            return false;
        }
    }

    return true;
    }

    function loadInfo(){
    const dropdown_ = document.getElementById('selectPreset');
    preset = dropdown_.value;
    $.ajax({
        type: 'POST',
        url: '/loadState',
        data: JSON.stringify({
            preset: preset
        }),
        contentType: 'application/json',
        success: function(response){
            const abproteinname = document.getElementById("abprotname");
            abproteinname.value = response.data.abproteinname;
            const protname = document.getElementById("protname");
            protname.value = response.data.proteinname;
            if (response.data.homo) {
                document.getElementById("zygosity2").checked = true;
                homochecked(true);
                document.getElementById("protlenhomo").value = response.data.homolen;
                const homostrucs = document.getElementById("homostrucs");
                while (homostrucs.firstChild) {
                    homostrucs.removeChild(homostrucs.firstChild);
                }
                response.data.homostructures.forEach((struc) => {
                    if(!deepEqual([], struc))
                    loadNewStrucContainer('homo', struc[0], struc[1], struc[2], struc[3]);
                });
                const homofeats = document.getElementById("featurecontainerhomo");
                while (homofeats.firstChild) {
                    homofeats.removeChild(homofeats.firstChild);
                }
                response.data.homofeatures.forEach((feat) => {
                    if(!deepEqual([], feat))
                    loadNewFeatureContainer('homo', feat[0], feat[1]);
                });
            }else{
                if (deepEqual(response.data.leftstructures, response.data.rightstructures)){
                    console.log('same protein structure');
                    document.getElementById("zygosity1").checked = true;
                    homochecked(false);
                    document.getElementById("sameradio1").checked = true;
                    document.getElementById("protlenleft").value = response.data.leftlen;
                    const leftstrucs = document.getElementById("leftstrucs");
                    while (leftstrucs.firstChild) {
                        leftstrucs.removeChild(leftstrucs.firstChild);
                    }
                    response.data.leftstructures.forEach((struc) => {
                        if(!deepEqual([], struc))
                        loadNewStrucContainer('left', struc[0], struc[1], struc[2], struc[3]);
                    });
                    const leftfeats = document.getElementById("featurecontainerleft");
                    while (leftfeats.firstChild) {
                        leftfeats.removeChild(leftfeats.firstChild);
                    }
                    response.data.leftfeatures.forEach((feat) => {
                        if(!deepEqual([], feat))
                        loadNewFeatureContainer('left', feat[0], feat[1]);
                    });
                    const rightfeats = document.getElementById("featurecontainerright");
                    while (rightfeats.firstChild) {
                        rightfeats.removeChild(rightfeats.firstChild);
                    }
                    response.data.rightfeatures.forEach((feat) => {
                        if(!deepEqual([], feat))
                        loadNewFeatureContainer('right', feat[0], feat[1]);
                    });
                    updateMirror();
                }else{
                    console.log('different protein structure');
                    document.getElementById("zygosity1").checked = true;
                    homochecked(false);
                    document.getElementById("sameradio2").checked = true;
                    updateMirror();
                    document.getElementById("protlenleft").value = response.data.leftlen;
                    const leftstrucs = document.getElementById("leftstrucs");
                    while (leftstrucs.firstChild) {
                        leftstrucs.removeChild(leftstrucs.firstChild);
                    }
                    response.data.leftstructures.forEach((struc) => {
                        if(!deepEqual([], struc))
                        loadNewStrucContainer('left', struc[0], struc[1], struc[2], struc[3]);
                    });
                    const rightstrucs = document.getElementById("rightstrucs");
                    while (rightstrucs.firstChild) {
                        rightstrucs.removeChild(rightstrucs.firstChild);
                    }
                    response.data.rightstructures.forEach((struc) => {
                        if(!deepEqual([], struc))
                        loadNewStrucContainer('right', struc[0], struc[1], struc[2], struc[3]);
                    });
                    const leftfeats = document.getElementById("featurecontainerleft");
                    while (leftfeats.firstChild) {
                        leftfeats.removeChild(leftfeats.firstChild);
                    }
                    response.data.leftfeatures.forEach((feat) => {
                        if(!deepEqual([], feat))
                        loadNewFeatureContainer('left', feat[0], feat[1]);
                    });
                    const rightfeats = document.getElementById("featurecontainerright");
                    while (rightfeats.firstChild) {
                        rightfeats.removeChild(rightfeats.firstChild);
                    }
                    response.data.rightfeatures.forEach((feat) => {
                        if(!deepEqual([], feat))
                        loadNewFeatureContainer('right', feat[0], feat[1]);
                    });
                }
            }
        },
        error: function() {
            alert("Error. Could not load presets.");
        }
    })
    }


    let right = 0;
    let left = 0;
    let homo = 0;

    function initializeStrucs(){
    addNewStrucContainer('left');
    const same = document.getElementById("sameradio1").checked;
    if (!same){
        addNewStrucContainer('right');
    }
    addNewStrucContainer('homo');
    homochecked();

    }

    function homochecked(){
    const samestrucradio1 = document.getElementById('sameradio1');
    const samestrucradio2 = document.getElementById('sameradio2');
    const homoradio = document.getElementById('zygosity2');
    const homocontainer = document.getElementById('homocontainer');
    const heterocontainer = document.getElementById('heterocontainer');
    if(homoradio.checked){
        samestrucradio1.disabled = true;
        samestrucradio2.disabled = true;
        homocontainer.classList.remove('hidden');
        heterocontainer.classList.add('hidden');
    }else{
        samestrucradio1.disabled = false;
        samestrucradio2.disabled = false;
        homocontainer.classList.add('hidden');
        heterocontainer.classList.remove('hidden');
    }


    }

    let featureright = 0;
    let featureleft = 0;
    let featurehomo = 0;

    function loadNewFeatureContainer(side, name, position) {
    const newFeatureContainer = document.createElement("div");

    let num = 0;
    if (side == 'left'){
        num = featureleft;
        featureleft++;
    }else if (side=='right'){
        num = featureright;
        featureright++;
    }else if(side=='homo'){
        num = featurehomo;
        featurehomo++;
    }

    newFeatureContainer.innerHTML = `
    <div class="round-container" id="feature`+side+num+`">
        <div class="row">
            <div class="col-4">
                <label for="featurename`+side+num+`" class="col-form-label">Feature Name</label>
            </div>
            <div class="col-8">
                <input type="featurename`+side+num+`" class="form-control" value="`+name+`">
            </div>
        </div>
        <div class="row">
            <div class="col-4">
                <label for="featurepos`+side+num+`" class="col-form-label">Feature Position</label>
            </div>
            <div class="col-8">
                <input type="featurepos`+side+num+`" class="form-control" value="`+position+`">
            </div>
        </div>
    </div>
    <span class="btn btn-light" id="deletefeature`+side+num+`" value="`+num+`" onclick="deleteFeature('`+side+`', this.getAttribute('value'))">Delete Feature</span>
    `
    const featureContainer = document.getElementById("featurecontainer"+side);
    featureContainer.appendChild(newFeatureContainer);

    }

    function addNewFeatureContainer(side) {
    const newFeatureContainer = document.createElement("div");

    let num = 0;
    if (side == 'left'){
        num = featureleft;
        featureleft++;
    }else if (side=='right'){
        num = featureright;
        featureright++;
    }else if(side=='homo'){
        num = featurehomo;
        featurehomo++;
    }

    newFeatureContainer.innerHTML = `
    <div class="round-container" id="feature`+side+num+`">
        <div class="row">
            <div class="col-4">
                <label for="featurename`+side+num+`" class="col-form-label">Feature Name</label>
            </div>
            <div class="col-8">
                <input type="featurename`+side+num+`" class="form-control">
            </div>
        </div>
        <div class="row">
            <div class="col-4">
                <label for="featurepos`+side+num+`" class="col-form-label">Feature Position</label>
            </div>
            <div class="col-8">
                <input type="featurepos`+side+num+`" class="form-control">
            </div>
        </div>
    </div>
    <span class="btn btn-light" id="deletefeature`+side+num+`" value="`+num+`" onclick="deleteFeature('`+side+`', this.getAttribute('value'))">Delete Feature</span>
    `
    const featureContainer = document.getElementById("featurecontainer"+side);
    featureContainer.appendChild(newFeatureContainer);

    }


    function loadNewStrucContainer(side, name, start, stop, color) {

    // Create a new struc-container element
    const newStrucContainer = document.createElement("div");
    newStrucContainer.className = "struc-container";

    let num = 0;
    if (side=='left'){
        num = left;
        left++;
    } else if (side=='right'){
        num = right;
        right++;
    } else if (side == 'homo'){
        num = homo;
        homo++;
    }

    newcolor=color;

    // Fill the new container with content (similar to the existing struc-container)
    newStrucContainer.innerHTML = `
        <div class="round-container color-container" style="background-color: `+newcolor+`" id="struc`+side+num+`">
            <div class="row">
                <div class="col-4">
                    <label for="protname`+side+num+`" class="col-form-label">Structure Name</label>
                </div>
                <div class="col-8">
                    <input type="protname`+side+num+`" class="form-control" value="`+name+`">
                </div>
            </div>
            <div class="row">
                <div class="col-4">
                    <label for="protstart`+side+num+`" class="col-form-label">Structure Start</label>
                </div>
                <div class="col-8">
                    <input type="protstart`+side+num+`" class="form-control" value="`+start+`">
                </div>
            </div>
            <div class="row">
                <div class="col-4">
                    <label for="protstop`+side+num+`" class="col-form-label">Structure Stop</label>
                </div>
                <div class="col-8">
                    <input type="protstop`+side+num+`" class="form-control" value="`+stop+`">
                </div>
            </div>
            <div class="row">
                <div class="col-4">
                    <label class="form-label">Color</label>
                </div>
                <div class="col-8">
                    <input type="color" class="form-control form-control-color" value="`+newcolor+`" id="color`+side+num+`" title="Choose your color" onchange="changeBackgroundColor(this.getAttribute('id'))">
                </div>
            </div>
        </div>
        <span class="btn btn-light" id="delete`+side+num+`" value="`+num+`" onclick="deleteStruc('`+side+`', this.getAttribute('value')); updateMirror()">Delete Structure</span>
        `;

    // Append the new struc-container to the container
    const strucContainer = document.getElementById(side+"strucs");
    strucContainer.appendChild(newStrucContainer);


    }

    function addNewStrucContainer(side, disableUpdate=false) {

    // Create a new struc-container element
    const newStrucContainer = document.createElement("div");
    newStrucContainer.className = "struc-container";

    let num = 0;
    if (side=='left'){
        num = left;
        left++;
    } else if (side=='right'){
        num = right;
        right++;
    } else if (side == 'homo'){
        num = homo;
        homo++;
    }

    newcolor=getRandomColor();

    // Fill the new container with content (similar to the existing struc-container)
    newStrucContainer.innerHTML = `
    <div class="round-container color-container" style="background-color: `+newcolor+`" id="struc`+side+num+`">
        <div class="row">
            <div class="col-4">
                <label for="protname`+side+num+`" class="col-form-label">Structure Name</label>
            </div>
            <div class="col-8">
                <input type="protname`+side+num+`" class="form-control">
            </div>
        </div>
        <div class="row">
            <div class="col-4">
                <label for="protstart`+side+num+`" class="col-form-label">Structure Start</label>
            </div>
            <div class="col-8">
                <input type="protstart`+side+num+`" class="form-control">
            </div>
        </div>
        <div class="row">
            <div class="col-4">
                <label for="protstop`+side+num+`" class="col-form-label">Structure Stop</label>
            </div>
            <div class="col-8">
                <input type="protstop`+side+num+`" class="form-control">
            </div>
        </div>
        <div class="row">
            <div class="col-4">
                <label class="form-label">Color</label>
            </div>
            <div class="col-8">
                <input type="color" class="form-control form-control-color" value="`+newcolor+`" id="color`+side+num+`" title="Choose your color" onchange="changeBackgroundColor(this.getAttribute('id'))">
            </div>
        </div>
    </div>
    <span class="btn btn-light" id="delete`+side+num+`" value="`+num+`" onclick="deleteStruc('`+side+`', this.getAttribute('value')); updateMirror()">Delete Structure</span>
    `;

    // Append the new struc-container to the container
    const strucContainer = document.getElementById(side+"strucs");
    strucContainer.appendChild(newStrucContainer);
    const same = document.getElementById("sameradio1");
    if (!disableUpdate){
        updateMirror()
    }


    }

    function changeBackgroundColor(identification) {
    console.log(identification);
    let leftRightValue = 'none';
    let number = '0';
    let selectedColor = "#000000";
    let strucContainer = '';
    if (identification.startsWith("colorleft")) {
        const parts = identification.match(/^(colorleft)(\d+)$/);
        if (parts && parts.length === 3) {
            leftRightValue = "left";
            number = parts[2];
        }
        const colorInput = document.getElementById("color"+leftRightValue+number);
        console.log("color"+leftRightValue+number);
        selectedColor = colorInput.value;
        strucContainer = document.getElementById("struc"+leftRightValue+number);

    } else if (identification.startsWith("colorright")) {
        const parts = identification.match(/^(colorright)(\d+)$/);
        if (parts && parts.length === 3) {
            leftRightValue = "right";
            number = parts[2];
        }
        const colorInput = document.getElementById("color"+leftRightValue+number);
        selectedColor = colorInput.value;
        strucContainer = document.getElementById("struc"+leftRightValue+number);

    } else {
        const parts = identification.match(/^(colorhomo)(\d+)$/);
        if (parts && parts.length === 3) {
            number = parts[2];
        }
        const colorInput = document.getElementById("colorhomo"+number);
        console.log("colorhomo"+number);
        selectedColor = colorInput.value;
        strucContainer = document.getElementById("struchomo"+number);

    }


    // Set the background color of the struc-container
    strucContainer.style.backgroundColor = selectedColor;

    updateMirror()
    }

    function deleteFeature(side, num) {
    const featureToRemove = document.getElementById('feature'+side+num);
    const buttonToRemove = document.getElementById('deletefeature'+side+num);
    buttonToRemove.remove()
    featureToRemove.remove()
    }

    function deleteStruc(side, num) {
    const strucToRemove = document.getElementById('struc'+side+num);
    const buttonToRemove = document.getElementById('delete'+side+num);
    buttonToRemove.remove();
    strucToRemove.remove();
    }

    function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
    }

    function generateFigure() {

    const protnamefield = document.getElementById("protname");
    const proteinname = protnamefield.value;

    const abprotnamefield = document.getElementById("abprotname");
    const abproteinname = abprotnamefield.value;

    const homoradio = document.getElementById('zygosity2');
    homo = homoradio.checked;
    console.log(homo);
    if (!homo){
        const leftstrucs = document.getElementById("leftstrucs");
        const leftitems = leftstrucs.children;
        const leftstructures = []
        for (let i = 0; i < leftitems.length; i++) {
            const leftitem = leftitems[i];
            const textFields = leftitems[i].querySelectorAll('.form-control');
            const strucvals = []
            for (let j = 0; j < textFields.length; j++) {
                strucvals.push(textFields[j].value);
            }
            leftstructures.push(strucvals);
        }
        
        const leftlenfield = document.getElementById("protlenleft");
        const leftlen = leftlenfield.value;

        let rightlen;
        let rightstructures;
        const same = document.getElementById("sameradio1").checked;
        if (same){
            rightlen = leftlen;
            rightstructures = leftstructures;
        }else{
            const rightstrucs = document.getElementById("rightstrucs");
            const rightitems = rightstrucs.children;
            rightstructures = []
            for (let i = 0; i < rightitems.length; i++) {
                const rightitem = rightitems[i];
                const textFields = rightitems[i].querySelectorAll('.form-control');
                const strucvals = []
                for (let j = 0; j < textFields.length; j++) {
                    strucvals.push(textFields[j].value);
                }
                rightstructures.push(strucvals);
            }
            const rightlenfield = document.getElementById("protlenright");
            rightlen = rightlenfield.value;
        }


        const leftfeaturecontainer = document.getElementById("featurecontainerleft");
        const leftfeatureitems = leftfeaturecontainer.children;
        const leftfeatures = []
        for (let i = 0; i < leftfeatureitems.length; i++) {
            const leftfeatureitem = leftfeatureitems[i];
            const textFields = leftfeatureitems[i].querySelectorAll('.form-control');
            const featurevals = []
            for (let j = 0; j < textFields.length; j++) {
                featurevals.push(textFields[j].value);
            }
            leftfeatures.push(featurevals);
        }
        const rightfeaturecontainer = document.getElementById("featurecontainerright");
        const rightfeatureitems = rightfeaturecontainer.children;
        const rightfeatures = []
        for (let i = 0; i < rightfeatureitems.length; i++) {
            const rightfeatureitem = rightfeatureitems[i];
            const textFields = rightfeatureitems[i].querySelectorAll('.form-control');
            const featurevals = []
            for (let j = 0; j < textFields.length; j++) {
                featurevals.push(textFields[j].value);
            }
            rightfeatures.push(featurevals);
        }

        

        $.ajax({
            type: 'POST',
            url: '/generatefigure',
            data: JSON.stringify({
                homo: homo,
                abproteinname: abproteinname,
                proteinname: proteinname,
                leftlen: leftlen,
                leftstructures: leftstructures,
                rightlen: rightlen,
                rightstructures: rightstructures,
                leftfeatures: leftfeatures,
                rightfeatures: rightfeatures
            }),
            contentType: 'application/json',
            success: function (response) {
                document.getElementById("resultcontainer").innerHTML += "";
            },
            error: function () {
                alert("Error. Are all fields correct?");
            }
        });
    }else{
        let homolen;
        let homostructures;
        const homostrucs = document.getElementById("homostrucs");
        const homoitems = homostrucs.children;
        homostructures = []
        for (let i = 0; i < homoitems.length; i++) {
            const homoitem = homoitems[i];
            const textFields = homoitems[i].querySelectorAll('.form-control');
            const strucvals = []
            for (let j = 0; j < textFields.length; j++) {
                strucvals.push(textFields[j].value);
            }
            homostructures.push(strucvals);
        }
        const homolenfield = document.getElementById("protlenhomo");
        homolen = homolenfield.value;

        const homofeaturecontainer = document.getElementById("featurecontainerhomo");
        const homofeatureitems = homofeaturecontainer.children;
        const homofeatures = []
        for (let i = 0; i < homofeatureitems.length; i++) {
            const homofeatureitem = homofeatureitems[i];
            const textFields = homofeatureitems[i].querySelectorAll('.form-control');
            const featurevals = []
            for (let j = 0; j < textFields.length; j++) {
                featurevals.push(textFields[j].value);
            }
            homofeatures.push(featurevals);
        }

        console.log(abproteinname);
        console.log(proteinname);
        console.log(homolen);
        console.log(homostructures);
        console.log(homofeatures);

        $.ajax({
            type: 'POST',
            url: '/generatefigure',
            data: JSON.stringify({
                homo: homo,
                abproteinname: abproteinname,
                proteinname: proteinname,
                homolen: homolen,
                homostructures: homostructures,
                homolen: homolen,
                homofeatures: homofeatures,
            }),
            contentType: 'application/json',
            success: function (response) {
                document.getElementById("resultcontainer").innerHTML += "";
            },
            error: function () {
                alert("Error. Are all fields correct?");
            }
        });

    }




    }

    const originalForm = document.getElementById('originalForm');
    const mirrorContainer = document.getElementById('mirrorContainer');

    function updateMirror() {
    // Clone the entire form
    const same = document.getElementById('sameradio1').checked;
    if (same){
        const clonedForm = originalForm.cloneNode(true);

        clonedForm.classList.remove('col-6');

        // Disable input elements and set their values
        clonedForm.querySelectorAll('input').forEach((input) => {
            input.disabled = true;
            input.value = input.value;

        });


        // Replace the mirror container with the cloned form

        mirrorContainer.innerHTML = '';

        mirrorContainer.appendChild(clonedForm);
    }
    else {

        const rightStrucContainer = document.getElementById("rightstrucs");
        if (!rightStrucContainer){
            mirrorContainer.innerHTML = `
                <div class="row" style="padding-bottom: 1rem;">
                    <div class="col-4">
                        <label for="protlenright" class="col-form-label">Protein Length (AA)</label>
                    </div>
                    <div class="col-8">
                        <input type="protlenright" id="protlenright" class="form-control">
                    </div>
                </div>
                <div id="rightstrucs" >
                </div>
                <span class="btn btn-light" onclick="addNewStrucContainer('right')">Add Structure</span>
                `;
            addNewStrucContainer('right', true);
        }

        
    }

    }


    // Attach an event listener to the original form elements
    originalForm.addEventListener('input', updateMirror);

    // Initial call to populate the mirrored elements
    updateMirror();