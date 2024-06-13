function updateInfo(id) {
    var statusElement = document.getElementById('status');
    var endTimeElement = document.getElementById('endTime');
    var runtimeElement = document.getElementById('runtime');
    var startTimeElement = document.getElementById('startTime');
    var computerElement = document.getElementById('computer');

    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/get_info/' + id);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var response = JSON.parse(xhr.responseText);
            statusElement.textContent = response.status;
            startTimeElement.textContent = response.startTime;
            endTimeElement.textContent = response.endTime;
            runtimeElement.textContent = response.runtime;
            computerElement.textContent = response.computer;
        }
    };
    xhr.send();
}

// Get the file name from the Flask route parameter (you may need to adapt this based on your actual route)

// Call the updateInfo function every second
if (status != "complete") {
    setInterval(function () {
        updateInfo(id);
        // if complete call function to make downloads appear
    }, 1000);
} else {
    // call function to make downloads appear
}