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

  const refreshHistoryBtn = document.getElementById("refresh-history-btn");
  if (refreshHistoryBtn) {
    refreshHistoryBtn.addEventListener("click", loadHistory);
  }

  // Load history on mount
  loadHistory();
});

async function loadHistory() {
  const container = document.getElementById("history-container");
  if (!container) return;
  container.innerHTML = `<p style="color: var(--text-secondary); font-size: 14px;">Loading...</p>`;

  try {
    const res = await fetch("/api/history");
    if (!res.ok) throw new Error("Failed to load history");
    const data = await res.json();

    if (!data.history || data.history.length === 0) {
      container.innerHTML = `<p style="color: var(--text-secondary); font-size: 14px;">No completed meetings found.</p>`;
      return;
    }

    container.innerHTML = "";
    data.history.forEach((mtg) => {
      const el = document.createElement("div");
      el.className =
        "bg-white/5 rounded-lg p-3 border border-white/10 cursor-pointer hover:bg-white/10 transition flex justify-between items-center";
      el.style =
        "background: rgba(255,255,255,0.2); border-radius: 8px; padding: 12px; cursor: pointer; border: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center; transition: all 0.2s;";

      const date = new Date(mtg.created_at).toLocaleDateString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
      el.innerHTML = `
        <span style="font-weight: 600; color: var(--text-primary); font-size: 15px;">${mtg.title || "Untitled Meeting"}</span>
        <span style="font-size: 13px; color: var(--text-secondary);">${date}</span>
      `;

      el.addEventListener("click", () => {
        document.getElementById("loader").textContent = "";
        document.getElementById("loader").className = "loader-hidden";
        // Convert to result schema explicitly
        const json = mtg.mom_json;
        if (json) {
          if (!json.title) json.title = mtg.title; // Inject DB title
          renderResults(json);
          window.scrollTo({
            top: document.getElementById("results-container").offsetTop,
            behavior: "smooth",
          });
        }
      });
      container.appendChild(el);
    });
  } catch (err) {
    container.innerHTML = `<p style="color: var(--danger); font-size: 14px;">Error: ${err.message}</p>`;
  }
}

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

function renderResults(result) {
  if (!result) return;

  document.getElementById("results-container").className = "results-visible";

  document.getElementById("res-summary").textContent = result.summary || "";

  const topicsList = document.getElementById("res-topics");
  topicsList.innerHTML = "";
  // Accept both schema formats dynamically
  const topics = result.key_topics || result.key_points || [];
  topics.forEach((k) => {
    const li = document.createElement("li");
    li.textContent = k;
    topicsList.appendChild(li);
  });

  const decisionsList = document.getElementById("res-decisions");
  decisionsList.innerHTML = "";
  if (result.decisions) {
    result.decisions.forEach((d) => {
      const li = document.createElement("li");
      const decText = d.decision || (typeof d === "string" ? d : "");
      const ctxText = d.context ? ` (${d.context})` : "";
      li.innerHTML = `<strong>${decText}</strong>${ctxText}`;
      decisionsList.appendChild(li);
    });
  }

  const actionsList = document.getElementById("res-actions");
  actionsList.innerHTML = "";
  if (result.action_items) {
    result.action_items.forEach((a) => {
      const li = document.createElement("li");
      const task = a.task || (typeof a === "string" ? a : "");
      const owner = a.owner || "Unassigned";
      const deadline = a.deadline ? ` (Due: ${a.deadline})` : "";
      li.innerHTML = `<strong>${task}</strong> - ${owner}${deadline}`;
      actionsList.appendChild(li);
    });
  }

  const qsList = document.getElementById("res-questions");
  qsList.innerHTML = "";
  const qs =
    result.open_questions ||
    (result.next_meeting_scheduled
      ? [`Next meeting: ${result.next_meeting_scheduled}`]
      : []);
  qs.forEach((q) => {
    const li = document.createElement("li");
    li.textContent = q;
    qsList.appendChild(li);
  });
}
