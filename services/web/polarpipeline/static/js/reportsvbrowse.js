// function to copy path to clipboard when clicked on
function copyToClipboard(text) {
    var textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
}

function openFileOptionsModal(fileName, filepath) {
    // Set the file name in the modal title
    $('#filePath').text(filepath)
    $('#fileOptionsModal').modal('show');
}

function closeFileOptionsModal() {
    $('#fileOptionsModal').modal('hide');
}

function startProcessing() {
    // closeFileOptionsModal()
    const filepath = document.getElementById('filePath').innerText;
    const sniffles = document.getElementById('textInput').value;
    const resultbox = document.getElementById('snifflesresult');
    resultbox.value = "loading...";
    console.log(filepath, sniffles);
    $.ajax({
        url: '/extractsniffles', // Flask route URL
        method: 'POST', // HTTP method
        contentType: 'application/json', // Content type for the request
        data: JSON.stringify({ path: filepath, id: sniffles }), // Convert data to JSON
        success: function(response) {
            // Handle successful response from Flask server
            // console.log(response);
            resultbox.value = response.join('\n');
        },
        error: function(xhr, status, error) {
            // Handle errors in the AJAX request
            resultbox.value ='Request failed:'+ status+ error;
        }
    });
}