document.addEventListener("DOMContentLoaded", () => {
    const generateBtn = document.getElementById("generate-btn");
    const transcriptInput = document.getElementById("transcript-input");
    const audioUpload = document.getElementById("audio-input");

    function toggleGenerateBtn() {
        const hasText = transcriptInput.value.trim().length > 0;
        const hasFile = audioUpload.files.length > 0;
        
        if (hasText || hasFile) {
            generateBtn.disabled = false;
            generateBtn.style.opacity = "1";
            generateBtn.style.cursor = "pointer";
        } else {
            generateBtn.disabled = true;
            generateBtn.style.opacity = "0.7";
            generateBtn.style.cursor = "not-allowed";
        }
    }

    transcriptInput.addEventListener("input", toggleGenerateBtn);
    audioUpload.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            transcriptInput.value = ""; 
            transcriptInput.disabled = true; 
        } else {
            transcriptInput.disabled = false;
        }
        toggleGenerateBtn();
    });
    
    generateBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        await generateMOM();
    });
});

async function generateMOM() {
    const input = document.getElementById("transcript-input").value;
    const fileInput = document.getElementById("audio-input");
    
    const resultsContainer = document.getElementById("results-container");
    const loader = document.getElementById("loader");

    if (!input.trim() && fileInput.files.length === 0) {
        alert("Please enter a meeting transcript or upload an audio file.");
        return;
    }

    loader.className = "loader";
    loader.textContent = "Initiating Vercel Pipeline...";
    resultsContainer.className = "results-hidden"; 

    const formData = new FormData();
    if (fileInput.files.length > 0) {
        formData.append("audio", fileInput.files[0]);
    } else {
        alert("Text upload currently unsupported in this demo phase.");
        return;
    }

    try {
        loader.textContent = "Uploading Audio & Starting Transcriber...";
        const transcribeRes = await fetch("/api/transcribe", {
            method: "POST",
            body: formData,
        });

        if (!transcribeRes.ok) throw new Error(`Upload failed: ${await transcribeRes.text()}`);

        const data = await transcribeRes.json();
        const meetingId = data.meeting_id;
        if (!meetingId) throw new Error("Did not receive meeting ID");

        loader.textContent = "Processing Audio on AssemblyAI. (Takes about 1/3 of the audio length)...";
        let status = "transcribing";
        
        while (status === "transcribing" || status === "queued") {
            await new Promise(r => setTimeout(r, 6000));
            const pollRes = await fetch(`/api/meetings?id=${meetingId}`);
            if (!pollRes.ok) continue;
            const pollData = await pollRes.json();
            
            if (pollData.error) throw new Error(pollData.error);
            if (pollData.error_message) throw new Error(pollData.error_message);
            status = pollData.processing_status;
        }

        if (status === "failed") throw new Error("Job failed during transcription phase");

        loader.textContent = "Transcription successful! Dispatching to Gemini (Groq Fallback active)...";
        const genRes = await fetch("/api/generate_mom", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: meetingId})
        });

        const genData = await genRes.json();
        if (genData.error) throw new Error(genData.error);
        
        renderResults(genData.result);
        loader.textContent = "Completed!";
    } catch (err) {
        console.error("Pipeline Error:", err);
        loader.textContent = "Pipeline Error!";
        alert(`Failed to generate Minutes of Meeting: ${err.message}`);
    } finally {
        setTimeout(() => { if (loader.textContent.includes("Completed")) loader.className = "loader-hidden"; }, 2000);
    }
}

function renderResults(result) {
    if (!result) return;
    
    document.getElementById("results-container").className = ""; 

    document.getElementById("res-summary").textContent = result.summary || "";
    
    const topicsList = document.getElementById("res-topics");
    topicsList.innerHTML = "";
    if (result.key_points) {
        result.key_points.forEach(k => {
            const li = document.createElement("li");
            li.textContent = k;
            topicsList.appendChild(li);
        });
    }

    const decisionsList = document.getElementById("res-decisions");
    decisionsList.innerHTML = "";
    if (result.decisions) {
        result.decisions.forEach(d => {
            const li = document.createElement("li");
            li.innerHTML = `<strong>${d.decision || ""}</strong>: ${d.context || ""}`;
            decisionsList.appendChild(li);
        });
    }

    const actionsList = document.getElementById("res-actions");
    actionsList.innerHTML = "";
    if (result.action_items) {
        result.action_items.forEach(a => {
            const li = document.createElement("li");
            li.innerHTML = `<strong>${a.task || ""}</strong> - ${a.owner || "Unassigned"} (By: ${a.deadline || "No Date"})`;
            actionsList.appendChild(li);
        });
    }

    const qsList = document.getElementById("res-questions");
    qsList.innerHTML = "";
    if (result.open_questions) {
        result.open_questions.forEach(q => {
            const li = document.createElement("li");
            li.textContent = q;
            qsList.appendChild(li);
        });
    }
}
