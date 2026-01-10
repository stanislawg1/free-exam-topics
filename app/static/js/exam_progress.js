const stageEl = document.getElementById("stage");
const messageEl = document.getElementById("message");
const progressContainer = document.getElementById("progress-container");
const progressEl = document.getElementById("progress");
const progressText = document.getElementById("progress-text");
const questionsEl = document.getElementById("questions");

const evt = new EventSource("/api/questions/progress");

evt.onmessage = (e) => {
    const data = JSON.parse(e.data);

    if (data.type === "stage") {
        stageEl.innerText = data.stage;
        messageEl.innerText = data.message || "";

        // pokaż progress bar tylko jeśli etap ma total
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
        stageEl.innerText = "Gotowe ✅";
        progressContainer.style.display = "none";
        evt.close();

        data.questions.forEach(q => {
            const div = document.createElement("div");
            div.innerText = q.text;
            questionsEl.appendChild(div);
        });
    }

    if (data.type === "error") {
        stageEl.innerText = "Błąd ❌";
        messageEl.innerText = data.message;
        evt.close();
    }
};
