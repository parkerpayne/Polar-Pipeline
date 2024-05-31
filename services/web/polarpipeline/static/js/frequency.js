function submitToVep(){
    const inputBox = document.getElementById("inputBox");
    const inputVal = inputBox.value;
    var regex = /chr(\w+)_(\w+)_(\w+)\/(\w+)/;
    var result = inputVal.replace(regex, "$1:$2:$3:$4");
    var encodedResult = encodeURIComponent(result);
    url = "/frequency/"+encodedResult;
    window.location.href = url;
}

function notification(){
    var progressBar = document.getElementById('progressbar');
    var notificationValue = document.getElementById('notificationValue');
    var barColor = notificationValue.value;

    if (barColor == "green"){
        progressBar.classList.add("bg-success");
    }
}

function beginsearch(){
    var progressBar = document.getElementById('progressbar');
    progressBar.classList.remove("bg-success");
}

function check_progress() {
    const progressContainer = $('#progressContainer');
    const progressBar = $('#progressBar');

    fetch('/frequencyprogress')
        .then(response => response.json())
        .then(progress => {
            console.log(progress);
            progressBar.css('width', (progress.progress * 100).toFixed(0) + "%");
            progressBar.attr('aria-valuenow', progress.progress);
            progressBar.text((progress.progress * 100).toFixed(0) + "%");

            // Show or hide progress container based on progress value
            if (progress.progress === 0) {
                // If progress is 0, hide progress container with slide up animation
                progressContainer.slideUp();
            } else {
                // If progress is not 0, show progress container with slide down animation
                progressContainer.slideDown();
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    setTimeout(check_progress, 1000);
}
check_progress();

function beginsearch(){
    $.ajax({
        type: 'POST',
        url: '/makefrequency',
        data: JSON.stringify({}),
        contentType: 'application/json',
        success: function (response) {
            if(response == 'success'){
                window.location.href = "/frequency";
            }
        },
        error: function (error) {
            alert('error: ' + error);
        }
    }); 
}
