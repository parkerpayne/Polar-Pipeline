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
    const notification = document.getElementById("notification");
    notification.style.opacity = "1";
    setTimeout(function () {
        notification.style.opacity = "0";
    }, 3000);// 3000 milliseconds (3 seconds)
}

function startProcessing() {
    closeFileOptionsModal()
    const filepath = document.getElementById('filePath').innerText;

    window.location.href = url = "/qc/"+filepath;
}