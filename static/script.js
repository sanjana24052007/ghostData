
/* =========================================
   GHOST DATA - DASHBOARD INTERACTIONS
========================================= */


/* 1. TABLE SEARCH */

function addTableSearch(inputId, tableId) {

    const searchInput = document.getElementById(inputId);
    const table = document.getElementById(tableId);

    if (!searchInput || !table) return;

    searchInput.addEventListener("input", function () {

        const searchText = this.value.toLowerCase().trim();

        const rows = table.querySelectorAll("tbody tr");

        rows.forEach(function (row) {

            const rowText = row.textContent.toLowerCase();

            row.style.display = rowText.includes(searchText)
                ? ""
                : "none";

        });

    });

}


/* 2. TABLE SORTING */

function enableTableSorting() {

    const tables = document.querySelectorAll("table");

    tables.forEach(function (table) {

        const headers = table.querySelectorAll("thead th");

        headers.forEach(function (header, columnIndex) {

            let ascending = true;

            header.title = "Click to sort";

            header.addEventListener("click", function () {

                const tbody = table.querySelector("tbody");

                if (!tbody) return;

                const rows = Array.from(
                    tbody.querySelectorAll("tr")
                ).filter(row => row.querySelectorAll("td").length > 1);

                rows.sort(function (rowA, rowB) {

                    const valueA = rowA.cells[columnIndex]
                        ?.textContent.trim() || "";

                    const valueB = rowB.cells[columnIndex]
                        ?.textContent.trim() || "";

                    const numberA = Number(valueA.replace(/,/g, ""));
                    const numberB = Number(valueB.replace(/,/g, ""));

                    let comparison;

                    if (
                        valueA !== "" &&
                        valueB !== "" &&
                        !isNaN(numberA) &&
                        !isNaN(numberB)
                    ) {
                        comparison = numberA - numberB;
                    } else {
                        comparison = valueA.localeCompare(
                            valueB,
                            undefined,
                            {
                                numeric: true,
                                sensitivity: "base"
                            }
                        );
                    }

                    return ascending ? comparison : -comparison;

                });

                rows.forEach(row => tbody.appendChild(row));

                ascending = !ascending;

            });

        });

    });

}


/* 3. ANIMATE RISK BARS */

function animateRiskBars() {

    const bars = document.querySelectorAll(".progress-fill");

    bars.forEach(function (bar) {

        const targetWidth = bar.style.width;

        bar.style.width = "0";

        requestAnimationFrame(function () {

            requestAnimationFrame(function () {
                bar.style.width = targetWidth;
            });

        });

    });

}


/* 4. SIDEBAR ACTIVE NAVIGATION */

function setupNavigation() {

    const navLinks = document.querySelectorAll(
        '.sidebar nav a[href^="#"]'
    );

    const sections = [];

    navLinks.forEach(function (link) {

        const section = document.querySelector(
            link.getAttribute("href")
        );

        if (section) {
            sections.push({
                link: link,
                section: section
            });
        }

        link.addEventListener("click", function () {

            navLinks.forEach(item =>
                item.classList.remove("active")
            );

            this.classList.add("active");

        });

    });

    if (!("IntersectionObserver" in window)) return;

    const observer = new IntersectionObserver(
        function (entries) {

            const visible = entries
                .filter(entry => entry.isIntersecting)
                .sort(
                    (a, b) =>
                        b.intersectionRatio - a.intersectionRatio
                );

            if (!visible.length) return;

            const currentSection = visible[0].target;

            navLinks.forEach(link => {

                link.classList.toggle(
                    "active",
                    link.getAttribute("href") ===
                    "#" + currentSection.id
                );

            });

        },
        {
            rootMargin: "-15% 0px -65% 0px",
            threshold: [0, 0.1, 0.25, 0.5]
        }
    );

    sections.forEach(item => observer.observe(item.section));

}


/* 5. SEARCH RESULT COUNTS */

function setupSearchCounts() {

    const searchInputs = document.querySelectorAll(".search-box");

    searchInputs.forEach(function (input) {

        const tableId = input.id === "caseSearch"
            ? "caseTable"
            : input.id === "highSearch"
                ? "highTable"
                : input.id === "evidenceSearch"
                    ? "evidenceTable"
                    : null;

        if (!tableId) return;

        const table = document.getElementById(tableId);

        if (!table) return;

        const rows = Array.from(
            table.querySelectorAll("tbody tr")
        ).filter(row => row.querySelectorAll("td").length > 1);

        let countDisplay = document.createElement("p");

        countDisplay.className = "subtitle";
        countDisplay.style.marginBottom = "12px";

        input.insertAdjacentElement("afterend", countDisplay);

        function updateCount() {

            const visibleCount = rows.filter(
                row => row.style.display !== "none"
            ).length;

            countDisplay.textContent =
                "Showing " + visibleCount +
                " of " + rows.length + " records";

        }

        input.addEventListener("input", updateCount);

        updateCount();

    });

}


/* 6. INITIALIZE DASHBOARD */

document.addEventListener("DOMContentLoaded", function () {

    // Search in all three tables
    addTableSearch("caseSearch", "caseTable");
    addTableSearch("highSearch", "highTable");
    addTableSearch("evidenceSearch", "evidenceTable");

    // Enable column sorting
    enableTableSorting();

    // Animate risk bars
    animateRiskBars();

    // Highlight current sidebar section
    setupNavigation();

    // Show search result counts
    setupSearchCounts();

    console.log("Ghost Data Dashboard Initialized Successfully");

});
