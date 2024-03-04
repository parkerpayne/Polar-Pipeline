
document.addEventListener("DOMContentLoaded", function () {
    const editButton = document.getElementById("editButton");
    const deleteButtons = document.querySelectorAll(".delete-button");
    const infoButtons = document.querySelectorAll(".info-button");

    editButton.addEventListener("click", function () {
        deleteButtons.forEach(function (button) {
            button.style.display = editButton.classList.contains("active") ? "none" : "inline-block";
        });
        infoButtons.forEach(function (button) {
            button.style.display = editButton.classList.contains("active") ? "inline-block" : "none";
        });

        editButton.classList.toggle("active");
    });
});

function handleDeleteClick(rowId) {
    const modalVal = document.getElementById("deleteItemModal");
    modalVal.value = rowId;
}

function deleteItem() {
    const modalVal = document.getElementById("deleteItemModal").value;
    window.location.href = "/deleteRun/" + modalVal
}