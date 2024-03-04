function convertFunction() {
    let inputText = document.getElementById("inputText").value.trim();
    let length = inputText.length
    if(length != 7 && length != 10)
    {
        convertedText = "Failure. Check input length?"
        showOutput(convertedText);
        return
    }
    else if(length == 10)
    {
        inputText = inputText.slice(3, 10)
    }
    t = []
    for(i=0; i<inputText.length; i++)
    {
        t.push(inputText.charAt(i))
    }
    convertedText = [t[6], t[2], t[1], t[3], t[5], t[4], t[0]]
    convertedText = convertedText.join("")
    if(length == 7)
    {
        convertedText = "030".concat(convertedText)
    }
    showOutput(convertedText);  
}

function showOutput(outputText) {
    document.getElementById("outputText").innerText = outputText;
    $('#outputModal').modal('show');
}
document.querySelector('form').addEventListener('submit', convertFunction);