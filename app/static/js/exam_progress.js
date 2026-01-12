const stageEl = document.getElementById("stage");
const messageEl = document.getElementById("message");
const progressContainer = document.getElementById("progress-container");
const progressEl = document.getElementById("progress");
const progressText = document.getElementById("progress-text");
const modeContainer = document.getElementById("mode-container");

const evt = new EventSource("/api/questions/progress");

evt.onmessage = (e) => {
    const data = JSON.parse(e.data);

    if (data.type === "stage") {
        stageEl.innerText = data.stage;
        messageEl.innerText = data.message || "";

        if (data.total) {
            progressContainer.style.display = "block";
            progressEl.value = 0;
            progressEl.max = data.total;
            progressText.innerText = `0 / ${data.total}`;
        } else {
            progressContainer.style.display = "none";
        }
    }

    if (data.type === "progress") {
        progressEl.value = data.current;
        progressText.innerText = `${data.current} / ${data.total}`;
        messageEl.innerText = data.message || "";
    }

    if (data.type === "done") {
        stageEl.style.display = "none";
        progressContainer.style.display = "none";
        messageEl.style.display = "none";

        if (modeContainer) {
            modeContainer.innerHTML = `
                <div class="mode-selector">
                    <h2>Choose mode:</h2>
                    <div class="mode-grid">
                        <a class="mode-tile" href="/${providerKey}/${examCode}/test">📝<span>Test mode</span></a>
                        <a class="mode-tile" href="/${providerKey}/${examCode}/learn">📘<span>Learn mode</span></a>
                        <a class="mode-tile" href="/${providerKey}/${examCode}/anki">🧠<span>Download Anki</span></a>
                    </div>
                </div>
            `;
        }

        evt.close();
    }

    if (data.type === "error") {
        stageEl.innerText = "Error ❌";
        messageEl.innerText = data.message;
        evt.close();
    }
};
