$(document).ready(function () {
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
        // Make an AJAX POST request to save_configuration endpoint
        $.ajax({
            type: 'POST',
            url: '/save_configuration',
            data: $(this).serialize(),
            success: function (data) {
                // Save the open configuration name in local storage before reloading the page
                localStorage.setItem('openConfig', computerName);
                location.reload();
            },
            error: function (error) {
                // Handle the error, if any.
                alert('An error occurred while saving the configuration.');
            }
        });
    });

    // After the page reloads, open the configuration dropdown that was open before the page was reloaded
    var openConfig = localStorage.getItem('openConfig');
    if (openConfig) {
        openConfigDropdown(openConfig);
        localStorage.removeItem('openConfig'); // Clear the stored value after opening the dropdown
    }
});

function chooseFile(inputId) {
    const fileInput = document.getElementById(inputId);
    fileInput.click();

    fileInput.addEventListener("change", function () {
        const form = fileInput.closest("form");
        form.submit();
    });
}

function removeItem(val){
    const encodedVal = encodeURIComponent(val);
    const redirectUrl = `/remove/${encodedVal}`;
    console.log(redirectUrl);
    window.location.href = redirectUrl;
}