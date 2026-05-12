
const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const resultsBox = document.getElementById("resultsBox");
const selectedBox = document.getElementById("selectedBox");
const searchStatus = document.getElementById("searchStatus");
const saveStatus = document.getElementById("saveStatus");
const saveBtn = document.getElementById("saveBtn");
const clearBtn = document.getElementById("clearBtn");
const countBadge = document.getElementById("countBadge");

const currentUrl = new URL(window.location.href);
if (!currentUrl.pathname.endsWith("/")) {
    currentUrl.pathname += "/";
}
currentUrl.search = "";
currentUrl.hash = "";
const settingsBaseUrl = currentUrl.toString();
const buildApiUrl = (path) => {
    const cleanPath = path.startsWith("/") ? path.slice(1) : path;
    return new URL(cleanPath, settingsBaseUrl).toString();
};

let selectedStations = [];

function updateCountBadge() {
    countBadge.textContent = "Selected: " + selectedStations.length;
}

function renderSelected() {
    selectedBox.innerHTML = "";
    if (!selectedStations.length) {
    selectedBox.textContent = "No stations selected yet.";
    updateCountBadge();
    return;
    }
    selectedStations.forEach((st, idx) => {
    const item = document.createElement("div");
    item.className = "item";

    const main = document.createElement("div");
    main.className = "item-main";

    const name = document.createElement("div");
    name.className = "item-name";
    name.textContent = st.name || "(unnamed station)";

    const meta = document.createElement("div");
    meta.className = "item-meta";
    meta.textContent = st.url;

    main.appendChild(name);
    main.appendChild(meta);

    const btn = document.createElement("button");
    btn.className = "secondary small-btn";
    btn.textContent = "Remove";
    btn.onclick = () => {
        selectedStations.splice(idx, 1);
        renderSelected();
    };

    item.appendChild(main);
    item.appendChild(btn);
    selectedBox.appendChild(item);
    });
    updateCountBadge();
}

function renderResults(stations) {
    resultsBox.innerHTML = "";
    if (!stations.length) {
    resultsBox.textContent = "No results.";
    return;
    }
    stations.forEach(st => {
    const url = st.url_resolved || st.url;
    if (!url) return;

    const item = document.createElement("div");
    item.className = "item";

    const main = document.createElement("div");
    main.className = "item-main";

    const name = document.createElement("div");
    name.className = "item-name";
    name.textContent = st.name || "(unnamed)";

    const meta = document.createElement("div");
    meta.className = "item-meta";
    const parts = [];
    if (st.country) parts.push(st.country);
    if (st.codec) parts.push(st.codec.toUpperCase());
    if (st.bitrate) parts.push(st.bitrate + " kbps");
    meta.textContent = parts.join(" · ") || url;

    main.appendChild(name);
    main.appendChild(meta);

    const btn = document.createElement("button");
    btn.className = "secondary small-btn";
    btn.textContent = "Add";
    btn.onclick = () => {
        selectedStations.push({ name: st.name || "(unnamed)", url });
        // dedupe on url
        const seen = new Set();
        selectedStations = selectedStations.filter(s => {
        const key = (s.url || "").toLowerCase();
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
        });
        renderSelected();
        saveStatus.textContent = "Not saved yet.";
        saveStatus.className = "status";
    };

    item.appendChild(main);
    item.appendChild(btn);
    resultsBox.appendChild(item);
    });
}

async function doSearch() {
    const q = searchInput.value.trim();
    if (!q) {
    searchStatus.textContent = "Type something to search.";
    searchStatus.className = "status err";
    resultsBox.innerHTML = "";
    return;
    }
    searchStatus.textContent = "Searching…";
    searchStatus.className = "status";
    resultsBox.innerHTML = "";

    try {
    const url = "https://de1.api.radio-browser.info/json/stations/search?name=" +
                encodeURIComponent(q) +
                "&limit=25&hidebroken=true";
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    renderResults(data);
    searchStatus.textContent = "Found " + data.length + " stations.";
    searchStatus.className = "status ok";
    } catch (err) {
    console.error(err);
    searchStatus.textContent = "Search failed.";
    searchStatus.className = "status err";
    }
}

async function loadSelectedFromServer() {
    try {
    const res = await fetch(buildApiUrl("api/webradios"));
    if (!res.ok) return;
    const data = await res.json();
    if (Array.isArray(data)) {
        selectedStations = data.map(s => ({
        name: s.name || "",
        url: s.url || ""
        }));
        renderSelected();
    }
    } catch (err) {
    console.error(err);
    }
}

async function saveToServer() {
    saveStatus.textContent = "Saving…";
    saveStatus.className = "status";
    try {
    const res = await fetch(buildApiUrl("api/webradios"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(selectedStations)
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    if (!data.ok) throw new Error("Server error");
    saveStatus.textContent = "Saved (" + data.count + " stations).";
    saveStatus.className = "status ok";
    } catch (err) {
    console.error(err);
    saveStatus.textContent = "Save failed.";
    saveStatus.className = "status err";
    }
}

searchBtn.onclick = () => doSearch();
searchInput.addEventListener("keydown", e => {
    if (e.key === "Enter") {
    e.preventDefault();
    doSearch();
    }
});

saveBtn.onclick = () => saveToServer();
clearBtn.onclick = () => {
    selectedStations = [];
    renderSelected();
    saveStatus.textContent = "Not saved yet.";
    saveStatus.className = "status";
};

// Initial load
loadSelectedFromServer();
