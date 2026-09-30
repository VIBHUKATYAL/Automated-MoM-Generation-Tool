document.addEventListener("DOMContentLoaded", () => {
  const generateBtn = document.getElementById("generate-btn");
  const transcriptInput = document.getElementById("transcript-input");
  const audioInput = document.getElementById("audio-input");
  const loader = document.getElementById("loader");
  const resultsContainer = document.getElementById("results-container");

  // UI Elements
  const resTranscriptCard = document.getElementById("refined-transcript-card");
  const resTranscript = document.getElementById("res-transcript");
  const resSummary = document.getElementById("res-summary");
  const resTopics = document.getElementById("res-topics");
  const resDecisions = document.getElementById("res-decisions");
  const resActions = document.getElementById("res-actions");
  const resQuestions = document.getElementById("res-questions");

  generateBtn.addEventListener("click", async () => {
    const transcript = transcriptInput.value.trim();
    const audioFile = audioInput.files.length > 0 ? audioInput.files[0] : null;

    if (!transcript && !audioFile) {
      alert("Please paste a transcript or upload an audio file.");
      return;
    }

    // UI Feedback
    loader.className = "loader-visible";
    generateBtn.disabled = true;
    generateBtn.style.opacity = "0.7";
    resultsContainer.className = "results-hidden";

    try {
      let response;
      if (audioFile) {
        // Use transcription endpoint
        const formData = new FormData();
        formData.append("audio", audioFile);

        response = await fetch("/api/transcribe_and_generate_mom", {
          method: "POST",
          body: formData,
        });
      } else {
        // Fallback to text transcript
        response = await fetch("/api/generate_mom", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ transcript }),
        });
      }

      if (!response.ok) {
        let errStr = "Server error occurred";
        try {
          const errData = await response.json();
          errStr = errData.error || errStr;
        } catch (e) {}
        throw new Error(errStr);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      resultsContainer.className = "results-visible";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop(); // keep the last incomplete chunk in the buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.substring(6);
            let data;
            try {
              data = JSON.parse(dataStr);
            } catch (e) {
              console.error("Failed to parse SSE JSON:", dataStr, e);
              continue;
            }
            // Bubble any errors thrown by handleStreamProgress up to the main catch block
            handleStreamProgress(data);
          }
        }
      }
    } catch (err) {
      console.error(err);
      alert("Failed to generate Minutes of Meeting: " + err.message);
    } finally {
      loader.className = "loader-hidden";
      generateBtn.disabled = false;
      generateBtn.style.opacity = "1";
    }
  });

  function handleStreamProgress(data) {
    if (data.status === "error") {
      throw new Error(data.message || data.error);
    }

    if (data.status === "transcribing_started")
      loader.textContent = "Transcribing Audio...";
    if (data.status === "refining_started")
      loader.textContent = `Refining Transcript (Chunk 1 of ${data.chunks})...`;
    if (data.status === "refining_progress")
      loader.textContent = `Refining Transcript (Chunk ${data.completed} of ${data.total})...`;
    if (data.status === "started")
      loader.textContent = `Generating MoM Overview...`;
    if (data.status === "progress") {
      loader.textContent = `Generating MoM (Chunk ${data.completed} of ${data.total})...`;
      if (data.partial) renderResults(data.partial, false);
    }
    if (data.status === "merging")
      loader.textContent = `Assembling Final Minutes...`;

    if (data.status === "completed") {
      loader.textContent = "Done!";
      if (data.transcript) {
        resTranscriptCard.style.display = "block";
        resTranscript.textContent = data.transcript;
      }
      renderResults(data.result, true);
    }
  }

  function renderResults(data, isFinal) {
    resSummary.textContent = data.summary || "N/A";

    // Topics
    resTopics.innerHTML = "";
    if (data.key_topics && data.key_topics.length > 0) {
      data.key_topics.forEach((t) => {
        const li = document.createElement("li");
        li.textContent = t;
        resTopics.appendChild(li);
      });
    } else {
      resTopics.innerHTML = "<li>None</li>";
    }

    // Decisions
    resDecisions.innerHTML = "";
    if (data.decisions && data.decisions.length > 0) {
      data.decisions.forEach((d) => {
        const li = document.createElement("li");
        li.textContent = d.decision + (d.context ? ` (${d.context})` : "");
        resDecisions.appendChild(li);
      });
    } else {
      resDecisions.innerHTML = "<li>None</li>";
    }

    // Actions
    resActions.innerHTML = "";
    if (data.action_items && data.action_items.length > 0) {
      data.action_items.forEach((a) => {
        const li = document.createElement("li");
        li.className = "action-item";

        const owner = document.createElement("div");
        owner.className = "action-owner";
        owner.textContent = a.owner || "Unassigned";

        const task = document.createElement("div");
        task.className = "action-task";
        task.textContent = a.task;

        li.appendChild(owner);
        li.appendChild(task);

        if (a.deadline) {
          const deadline = document.createElement("div");
          deadline.className = "action-deadline";
          deadline.innerHTML = `<i class="ph ph-clock"></i> ${a.deadline}`;
          li.appendChild(deadline);
        }

        resActions.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.textContent = "None";
      resActions.appendChild(li);
    }

    // Open Questions
    resQuestions.innerHTML = "";
    if (data.open_questions && data.open_questions.length > 0) {
      data.open_questions.forEach((q) => {
        const li = document.createElement("li");
        li.textContent = q;
        resQuestions.appendChild(li);
      });
    } else {
      resQuestions.innerHTML = "<li>None</li>";
    }

    if (isFinal) {
      resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
});
