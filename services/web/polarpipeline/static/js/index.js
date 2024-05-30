// =============================================================================
//     DEPRICATED (used to be a button that would allow for file uploads)
// =============================================================================
// function updateFileLabel(input) {
//     var fileName = input.files[0].name;
//     var label = input.nextElementSibling;
//     label.textContent = fileName;
// }
// // Function to disable the submit button and change its color while uploading
// function disableSubmitButton() {
//     var submitBtn = document.getElementById('submitBtn');
//     submitBtn.disabled = true;
//     submitBtn.classList.add('btn-uploading');
// }


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
    // Set the file name in the modal title
    $('#filePath').text(filepath)
    $('#fileOptionsModal').modal('show');
}

function closeFileOptionsModal() {
    $('#fileOptionsModal').modal('hide');
    const notification = document.getElementById("notification");
    notification.style.opacity = "1";
    setTimeout(function () {
        notification.style.opacity = "0";
    }, 3000);// 3000 milliseconds (3 seconds)
}

function getSelectedBedFiles(whatType) {
    var bedFileCheckboxes = document.querySelectorAll("input[type=checkbox]:checked");
    var selectedBedFiles = [];

    bedFileCheckboxes.forEach(function(item) {
        var bed = item.id;
        if (bed.endsWith(whatType)) {
            end = "Checkbox"+whatType;
            selectedBedFiles.push(bed.replace(end, ""))
        }
    });

    return selectedBedFiles;
}

function getGeneSourceSelection(bedFiles) {
    var gene_sources = [];
    bedFiles.forEach(function(item) {
        const geneSourceSelect = document.getElementById(`${item}GeneSourceSelect`);
        const selectedGeneSource = geneSourceSelect.value;
        gene_sources.push(selectedGeneSource)
    });
    
    return gene_sources;
}

function startProcessing() {
    var outputpath = document.querySelector("#outputSelect").value;
    var selectedClairModel = document.querySelector("#clairModelSelect").value;
    var filepath = document.getElementById("filePath").textContent;

    var grch_reference_file = 'none';
    var grch_bed_files = 'none';
    var grch_gene_sources = 'none';
    var chm_reference_file = 'none';
    var chm_bed_files = 'none';

    if (document.getElementById("inlineCheckbox1").checked) {
        grch_reference_file = document.querySelector("#referenceFileSelectGRCH38").value;
        grch_bed_files = getSelectedBedFiles("GRCH38");
        grch_gene_sources = getGeneSourceSelection(grch_bed_files)
    }
    if (document.getElementById("inlineCheckbox2").checked) {
        chm_reference_file = document.querySelector("#referenceFileSelectchm13").value;
        chm_bed_files = getSelectedBedFiles("chm13");
    }

    if(grch_reference_file == 'none' && chm_reference_file == 'none'){
        alert('Reference file is required.');
        return;
    }

    closeFileOptionsModal()

    $.ajax({
        type: 'POST',
        url: '/trigger_processing',
        data: JSON.stringify({
            path: filepath,
            output_path: outputpath,
            clair: selectedClairModel,
            grch_reference: grch_reference_file,
            grch_bed: grch_bed_files,
            chm_reference: chm_reference_file,
            chm_bed: chm_bed_files,
            grch_gene: grch_gene_sources
        }),
        contentType: 'application/json',
        success: function (response) {
            console.log('success');
        },
        error: function () {
            console.log('error');
        }
    });
}
// Function to toggle the disabled attribute of forms
function toggleForm(formId) {
    var form = document.getElementById(formId);
    var checkbox = document.getElementById('inlineCheckbox' + (formId === 'grch38' ? '1' : '2'));
    
    if (checkbox.checked) {
        form.style.display = 'block';
        form.removeAttribute('disabled');
    } else {
        form.style.display = 'none';
        form.setAttribute('disabled', 'disabled');
    }
}

function toggleGeneSource(bedFile) {
    var geneSourceSelect = document.getElementById(bedFile + "GeneSourceSelect");
    var checkbox = document.getElementById(bedFile + "CheckboxGRCH38");

    if (checkbox.checked) {
        geneSourceSelect.style.display = "block"; // Show gene source dropdown
    } else {
        geneSourceSelect.style.display = "none"; // Hide gene source dropdown
    }
}

var outputSelect = document.getElementById('outputSelect');
outputSelect.addEventListener('change', function() {
    var selectedOutput = outputSelect.value;
    localStorage.setItem('selectedOutput', selectedOutput);
});
var storedOutput = localStorage.getItem('selectedOutput');
if (storedOutput) {
    outputSelect.value = storedOutput;
}