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
    loader.textContent = "Uploading Audio & Starting Transcriber...";
  } else if (input.trim() !== "") {
    formData.append("text", input.trim());
    loader.textContent =
      "Dispatching Transcript directly to Map-Reduce Pipeline...";
  } else {
    alert("Please provide either text or audio.");
    return;
  }

  try {
    const transcribeRes = await fetch("/api/transcribe", {
      method: "POST",
      body: formData,
    });

    if (!transcribeRes.ok)
      throw new Error(`Upload failed: ${await transcribeRes.text()}`);

    const data = await transcribeRes.json();
    const meetingId = data.meeting_id;
    if (!meetingId) throw new Error("Did not receive meeting ID");

    let status = data.status || "transcribing";
    if (status === "transcribing") {
      loader.textContent =
        "Processing Audio on AssemblyAI. (Takes about 1/3 of the audio length)...";
    }

    while (status === "transcribing" || status === "queued") {
      await new Promise((r) => setTimeout(r, 6000));
      const pollRes = await fetch(`/api/meetings?id=${meetingId}`);
      if (!pollRes.ok) continue;
      const pollData = await pollRes.json();

      if (pollData.error) throw new Error(pollData.error);
      if (pollData.error_message) throw new Error(pollData.error_message);
      status = pollData.processing_status;
    }

    if (status === "failed")
      throw new Error("Job failed during transcription phase");

    loader.textContent =
      "Transcription successful! Dispatching to Gemini (Groq Fallback active)...";
    const genRes = await fetch("/api/generate_mom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: meetingId }),
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
    setTimeout(() => {
      if (loader.textContent.includes("Completed"))
        loader.className = "loader-hidden";
    }, 2000);
  }
}

function renderResults(mom) {
  if (!mom) return;

  const resultsContainer = document.getElementById("results-container");
  resultsContainer.className = "";

  let html = "";
  if (mom.title) {
    html += `<div class="mb-4 border-b border-white/20 pb-2">
                    <strong class="text-white text-xl font-bold">${mom.title}</strong>
                 </div>`;
  }
  if (mom.attendees && mom.attendees.length > 0) {
    html += `<div class="mb-4">
                    <strong class="text-white text-lg">Attendees</strong>
                    <p class="text-white/80 mt-1">${mom.attendees.join(", ")}</p>
                 </div>`;
  }

  // Build Summary
  html += `<div class="mb-4">
                <strong class="text-white text-lg">Summary</strong>
                <p class="text-white/80 mt-1">${mom.summary}</p>
             </div>`;

  // Build Key Points / Topics
  let kp = mom.key_topics || mom.key_points || [];
  if (kp.length > 0) {
    html += `<div class="mb-4">
                    <strong class="text-white text-lg">Key Points</strong>
                    <ul class="list-disc pl-5 mt-1 text-white/80">`;
    kp.forEach((point) => {
      html += `<li>${point}</li>`;
    });
    html += `</ul></div>`;
  }

  // Build Decisions
  if (mom.decisions && mom.decisions.length > 0) {
    html += `<div class="mb-4">
                    <strong class="text-white text-lg">Decisions Made</strong>
                    <ul class="list-disc pl-5 mt-1 text-white/80">`;
    mom.decisions.forEach((d) => {
      let text = d.decision;
      if (d.context)
        text += ` <span class="text-white/50 text-sm">(${d.context})</span>`;
      html += `<li>${text}</li>`;
    });
    html += `</ul></div>`;
  }

  // Build Action Items
  if (mom.action_items && mom.action_items.length > 0) {
    html += `<div class="mb-4">
                    <strong class="text-white text-lg">Action Items</strong>
                    <div class="mt-2 grid grid-cols-1 gap-2">`;
    mom.action_items.forEach((a) => {
      let task = a.task;
      let owner = a.owner || "Unassigned";
      let ded = a.deadline ? `Due: ${a.deadline}` : "No deadline";
      html += `
            <div class="bg-white/5 rounded-lg p-3 border border-white/10 flex flex-col md:flex-row md:items-center justify-between">
                <span class="text-white/90">${task}</span>
                <div class="mt-2 md:mt-0 flex flex-row gap-2">
                    <span class="bg-[#121212] px-2 py-1 rounded text-xs text-white/60">${owner}</span>
                    <span class="bg-[#121212] px-2 py-1 rounded text-xs text-[#00ff88]/80">${ded}</span>
                </div>
            </div>`;
    });
    html += `</div></div>`;
  }

  // Build Open Questions
  if (mom.open_questions && mom.open_questions.length > 0) {
    html += `<div class="mb-4">
                    <strong class="text-white text-lg">Open Questions</strong>
                    <ul class="list-disc pl-5 mt-1 text-white/80">`;
    mom.open_questions.forEach((q) => {
      html += `<li>${q}</li>`;
    });
    html += `</ul></div>`;
  }

  resultsContainer.innerHTML = html;
}
