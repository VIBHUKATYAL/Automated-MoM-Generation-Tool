document.addEventListener("DOMContentLoaded", () => {
    const generateBtn = document.getElementById("generate-btn");
    
    generateBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        await generateMOM();
    });
});

async function generateMOM() {
    const input = document.getElementById("transcript-input").value;
    const fileInput = document.getElementById("audio-upload");
    const resultDiv = document.getElementById("result");
    const loader = document.getElementById("loader");

    if (!input.trim() && fileInput.files.length === 0) {
        alert("Please enter a meeting transcript or upload an audio file.");
        return;
    }

    loader.className = "loader";
    loader.textContent = "Initiating Pipeline...";
    resultDiv.innerHTML = "";

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

        loader.textContent = "Processing Audio on AssemblyAI. This may take 1-2 minutes...";
        let status = "transcribing";
        
        while (status === "transcribing" || status === "queued") {
            await new Promise(r => setTimeout(r, 5000));
            const pollRes = await fetch(`/api/meetings?id=${meetingId}`);
            const pollData = await pollRes.json();
            
            if (pollData.error) throw new Error(pollData.error);
            if (pollData.error_message) throw new Error(pollData.error_message);
            status = pollData.processing_status;
        }

        if (status === "failed") throw new Error("Job failed during transcription phase");

        loader.textContent = "Transcription successful. Starting Gemini/Groq Fallback Phase...";
        const genRes = await fetch("/api/generate_mom", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: meetingId})
        });

        const genData = await genRes.json();
        if (genData.error) throw new Error(genData.error);
        if (genData.error_message) throw new Error(genData.error_message);
        
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
    const resultDiv = document.getElementById("result");
    if (!result) return;
    
    let html = `<div class="result-card"><h3>Meeting Summary</h3><p>${result.summary}</p></div>`;
    
    if (result.key_points && result.key_points.length > 0) {
        html += `<div class="result-card"><h3>Key Points</h3><ul>${result.key_points.map(h => `<li>${h}</li>`).join("")}</ul></div>`;
    }
    
    if (result.decisions && result.decisions.length > 0) {
        html += `<div class="result-card"><h3>Decisions</h3><ul>${result.decisions.map(d => `<li><strong>${d.decision || ""}</strong>: ${d.context || ""}</li>`).join("")}</ul></div>`;
    }
    
    if (result.action_items && result.action_items.length > 0) {
        html += `<div class="result-card"><h3>Action Items</h3><ul>${result.action_items.map(a => `<li><strong>${a.task || ""}</strong> - ${a.owner || "Unassigned"} (By: ${a.deadline || "No Date"})</li>`).join("")}</ul></div>`;
    }
    
    if (result.next_meeting_scheduled) {
         html += `<div class="result-card"><h3>Next Meeting</h3><p>${result.next_meeting_scheduled}</p></div>`;
    }

    resultDiv.innerHTML = html;
}
