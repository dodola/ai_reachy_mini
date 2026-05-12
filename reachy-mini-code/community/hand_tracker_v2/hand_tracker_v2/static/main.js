const toggleVideo = document.getElementById("toggle-video");
const videoFeed = document.getElementById("video-feed");
const toggleTracking = document.getElementById("toggle-tracking");
const toggleAntenna = document.getElementById("toggle-antennas");



const videoSrc = "/video_feed";

toggleVideo.addEventListener("change", () => {
    if (toggleVideo.checked) {
        videoFeed.src = videoSrc;
    } else {
        videoFeed.src = "";
    }
});


async function updateToggleState() {
    try {
        const resp = await fetch("/set_toggles", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video: toggleVideo.checked,
                tracking: toggleTracking.checked,
                antenna: toggleAntenna.checked,
                preferred_side: document.getElementById("side-select").value,
                antenna_mode: document.getElementById("antenna-mode").value
            })
        });
        const data = await resp.json();

    } catch (e) {
        console.error(e);
        document.getElementById("status").textContent = "Server error";
    }
}

async function waitForAppReady() {
    while (true) {
        try {
            const resp = await fetch("/ready");
            console.log("ready status:", resp.status);
            const data = await resp.json();
            console.log("ready payload:", data);
            if (data.ready) {
                document.getElementById("loading-overlay").style.display = "none";
                return;
            }
        } catch (e) {
            console.error("ready fetch error", e);
        }
        await new Promise(r => setTimeout(r, 500));
    }
}


waitForAppReady();


// Ajouter un event listener à chaque toggle
[toggleVideo, toggleTracking, toggleAntenna].forEach(toggle => {
    toggle.addEventListener("change", updateToggleState);
});
document.getElementById("side-select").addEventListener("change", updateToggleState);
document.getElementById("antenna-mode").addEventListener("change", updateToggleState);
