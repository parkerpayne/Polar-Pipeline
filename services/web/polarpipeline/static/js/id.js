function convertFunction(btn = null) {
    let inputText = document.getElementById("inputText").value.trim();
    var data = {input: inputText}
    if(btn){
        data = {input: inputText, inputtype: btn.value};
    }
    $.ajax({
        url: '/id_coding',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(response) {
            if(response === "specify"){
                $('#clarifyModal').modal('show');
            }else if(response === "error"){
                alert("Error: Unable to perform operation");
            }else{
                showOutput(response);
            }
        },
        error: function(xhr, status, error) {
            // Handle error response from the server
            alert('Error: '+ error);
        }
    });
}

function showOutput(outputText) {
    document.getElementById("outputText").innerText = outputText;
    $('#outputModal').modal('show');
}
document.querySelector('form').addEventListener('submit', convertFunction);

var newOrder = [];
var staticBox = $('#staticnums');
var adjacencyalert = $('#adjacency-alert');

function staticBoxes(box, isTyping) {
    // Get all input elements with the same id
    var boxes = $("[id='" + box.id + "']");

    if (isTyping) {
        // Find the index of the current box
        var currentIndex = boxes.index(box);

        // If there's a next box, focus on it and select its text
        if (currentIndex < boxes.length - 1) {
            var nextBox = boxes[currentIndex + 1];
            nextBox.focus();
            nextBox.select();
        } else {
            // If there are no more boxes, remove focus from the current box
            box.blur();
        }
    } else {
        // Highlight the text in the box
        box.select();
    }
}

function checkAdjacency(input){
    for (var i = 0; i < input.length - 1; i++) {
        var current = parseInt(input[i].text(), 10);
        var next = parseInt(input[i + 1].text(), 10);
        if (next !== current + 1) {
            return false;
        }
    }
    return true;
}

function updateOrder(){
    var ogOrder = [];
    newOrder.forEach(element => {
        ogOrder.push(element);
    });
    newOrder = [];
    $("#sortableList .list-group-item-text").each(function() {
        newOrder.push($(this));
    });

    var omitIndex = newOrder.findIndex(function(element) {
        return element.text() === "Omit";
    });

    var omittedVals = [];
    if (omitIndex !== -1 && omitIndex < newOrder.length - 1) {
        for (var i = omitIndex + 1; i < newOrder.length; i++) {
            omittedVals.push(newOrder[i]);
        }
        omittedVals.sort(function(a, b) {
            var intA = parseInt(a.text(), 10);
            var intB = parseInt(b.text(), 10);
            return intA - intB;
        });

        var parentElement = omittedVals[0].parent().parent();
        omittedVals.forEach(function(element) {
            parentElement.append(element.parent());
        });

        if (!checkAdjacency(omittedVals)){
            adjacencyalert.slideDown();
        }else{
            adjacencyalert.slideUp();
        }

        var numboxes = numboxes = $('#textboxrow .col-auto').length;
        while(numboxes < omittedVals.length) {
            var textBox = `<div class="col-auto" id="staticnumcol"><input class="form-control static-num-box" id="staticnumfield" onkeypress="staticBoxes(this, true)" onclick="staticBoxes(this, false)"></div>`;
            $("#textboxrow").append(textBox);
            numboxes = numboxes = $('#textboxrow .col-auto').length;
        }
        while (numboxes > omittedVals.length) {
            $('#textboxrow .col-auto:last').remove();
            numboxes = $('#textboxrow .col-auto').length;
        }
        staticBox.slideDown();
    } else {
        adjacencyalert.slideUp();
        staticBox.slideUp();
    }
}

function addNumber(){
    var num = $('.list-group-item').length;
    var box = `<li class="list-group-item">        
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-list" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M2.5 12a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5"/>
                    </svg>
                    <span class="list-group-item-text">`+num+`</span>
                </li>`
    var omitIndex = $("#sortableList .list-group-item-text").filter(function() {
        return $(this).text() === "Omit";
    }).closest('.list-group-item').index();
    if (omitIndex !== -1) {
        $("#sortableList .list-group-item").eq(omitIndex).before(box);
    }else{
        $("#sortableList").append(box);
        updateOrder();
    }   
}

function removeNumber(){
    var num = $('.list-group-item').length - 1;
    var toremove = $("#sortableList .list-group-item-text").filter(function() {
        return $(this).text() === num.toString();
    });
    if(num > 0){
        toremove.parent().remove();
        updateOrder();
    }
}

function savePattern(){
    encode = []
    Array.from($("#sortableList .list-group-item-text")).forEach(element => {
        var pos = element.innerText;
        if(pos === 'Omit'){
            pos = '|';
        }
        encode.push(pos);
    });
    var static = [];
    Array.from($(".static-num-box")).forEach(element => {
        static.push(element.value);
    });

    var data = {
        encode: encode,
        static: static
    };

    $.ajax({
        url: '/save_pattern',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(response) {
            if(response === "lengths"){
                alert("Error: lengths of omitted positions and omitted values do not match");
            }else if(response === "emptyomission"){
                alert("Error: Values for all omitted positions must be provided");
            }else if(response === "nopositions"){
                alert("Error: There must be non-omitted positions");
            }else if(response === "adjacent"){
                alert("Error: Omitted positions must be adjacent");
            }else{
                $('#patternModal').modal('hide');
                const notification = document.getElementById("notification");
                notification.style.opacity = "1";
                setTimeout(function () {
                    notification.style.opacity = "0";
                }, 3000);
            }
        },
        error: function(xhr, status, error) {
            // Handle error response from the server
            alert('Error saving pattern: '+ error);
        }
    });
}

$(function() {
    $("#sortableList").sortable({
        update: function(event, ui) {
            // console.log("Reordering occurred!");
            updateOrder();
            // console.log("New order:", newOrder);
        }
    });
    updateOrder();
    // console.log("Initial order:", newOrder);
    $("#sortableList").disableSelection();
});
