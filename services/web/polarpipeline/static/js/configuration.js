$(document).ready(function () {
    var pathfields = $('.PathField')
    Array.from(pathfields).forEach(element => {
        if(!element.disabled){
            element.disabled = true;
        }
    });
    // Function to open the configurations dropdown for a specific computer name
    function openConfigDropdown(computerName) {
        var dropdown = $('input[name="computer_name"][value="' + computerName + '"]').closest('.config-dropdown-form').find('.configurations-dropdown');
        dropdown.addClass('show');
    }

    // Toggle configurations dropdown
    $('.config-dropdown-form .dropdown-toggle').on('click', function () {
        var dropdown = $(this).parent().parent().find('.configurations-dropdown');
        dropdown.toggleClass('show');
    });

    // Show confirmation modal when the delete button is clicked
    $('.delete-config-btn').on('click', function () {
        var computerName = $(this).closest('.config-dropdown-form').find('input[name="computer_name"]').val();
        $('#confirmDeleteBtn').data('computerName', computerName); // Store the computer name in the delete button data attribute
        $('#deleteConfirmationModal').modal('show');
    });

    // Handle the delete confirmation
    $('#confirmDeleteBtn').on('click', function () {
        var computerName = $(this).data('computerName');

        // Make an AJAX POST request to delete_configuration endpoint
        $.ajax({
            type: 'POST',
            url: '/delete_configuration',
            data: { computer_name: computerName },
            success: function (data) {
                // Save the open configuration name in local storage before reloading the page
                location.reload();
            },
            error: function (error) {
                // Handle the error, if any.
                alert('An error occurred while deleting the configuration.');
            }
        });

        $('#deleteConfirmationModal').modal('hide');
    });

    // Handle the save configuration
    $('.config-dropdown-form').on('submit', function (event) {
        event.preventDefault(); // Prevent the form from submitting normally

        var computerName = $(this).find('input[name="computer_name"]').val();
        var config_data = $(this).serialize();
        if (computerName == "Output"){
            var formData = $(this).serializeArray();
    
            var outputPaths = formData.filter(function(item) {
                return item.name === 'Output' && item.value.trim() !== '';
            }).map(function(item) {
                return item.value;
                
            }).join(';');
            
            formData = formData.filter(function(item) {
                return item.name !== 'Output';
            });
            formData.push({name: 'Output', value: outputPaths});
            
            config_data = $.param(formData);
            
            console.log(config_data);
        }

        // Make an AJAX POST request to save_configuration endpoint
        $.ajax({
            type: 'POST',
            url: '/save_configuration',
            data: config_data,
            success: function (data) {
                // Save the open configuration name in local storage before reloading the page
                const notification = document.getElementById("notification");
                notification.style.opacity = "1";
                setTimeout(function () {
                    notification.style.opacity = "0";
                }, 3000);// 3000 milliseconds (3 seconds)
            },
            error: function (error) {
                // Handle the error, if any.
                alert('An error occurred while saving the configuration.');
            }
        });
    });
});

function chooseFile(inputId) {
    const fileInput = document.getElementById(inputId);
    fileInput.click();

    fileInput.addEventListener("change", function () {
        const form = fileInput.closest("form");
        if (inputId == "fileInput1"){
            const selectedFile = fileInput.files[0];
            if (!selectedFile.name.endsWith('.zip') && !selectedFile.name.endsWith('.gz')) {
                alert('Clair3 models are folders, so a zip must be uploaded!');
                return;
            }
        }
        form.submit();
        
    });
}

function removeItem(val){
    const encodedVal = encodeURIComponent(val);
    const redirectUrl = `/remove/${encodedVal}`;
    console.log(redirectUrl);
    window.location.href = redirectUrl;
}

function toggleEdit(type){
    const edittype = type + '-btn';
    var buttons = document.getElementsByClassName(edittype);
    Array.from(buttons).forEach(element => {
        if (element.classList.contains('PathField')){
            if (element.disabled){
                element.disabled = false;
            }else{
                element.disabled = true;
            }
        }else{
            element.classList.toggle('invisible-button');
        }
        
    });
}

function generateList(btn){
    btn.onclick = '';
    var rawpaths = $('.PathField');
    toggleEdit('populate-text');
    var paths = [];
    Array.from(rawpaths).forEach(element => {
        paths.push(element.value);
    });
    var populateModalTarget = document.getElementById('populateModalTarget');
    fetch('/requestdbs', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(paths)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.blob();
    })
    .then(blob => {
        console.log('test');
    })
    .catch(error => {
        // Handle error
        console.error('Error:', error);
    });

}

function newPath() {
    var path = document.createElement("div")
    path.innerHTML = `<input type="text" class="form-control output-path-box mb-2" id="Output" name="Output"></input>`;
    container = document.getElementById('output-path-container');
    container.appendChild(path);
}