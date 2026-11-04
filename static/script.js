
function addTableSearch(inputId, tableId) {
    const searchInput = document.getElementById(inputId);
    const table = document.getElementById(tableId);

    if (!searchInput || !table) return;

    searchInput.addEventListener("input", function () {
        const searchText = this.value.toLowerCase();
        const rows = table.querySelectorAll("tbody tr");

        rows.forEach(function (row) {
            const rowText = row.textContent.toLowerCase();

            row.style.display = rowText.includes(searchText)
                ? ""
                : "none";
        });
    });
}

document.addEventListener("DOMContentLoaded", function () {
    addTableSearch("highSearch", "highTable");
    addTableSearch("evidenceSearch", "evidenceTable");
});
