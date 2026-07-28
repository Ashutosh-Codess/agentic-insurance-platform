// Handles the copilot chat box on pages/copilot.html - sends a question,
// streams the answer into the page as it arrives.

async function sendCopilotQuestion(predefinedQuestion = null) {
  const collection = document.getElementById("copilot-collection").value;
  const questionInput = document.getElementById("copilot-question");
  const question = predefinedQuestion || questionInput.value;
  const answerBox = document.getElementById("copilot-answer");
  const btn = document.getElementById("copilot-btn");

  if (!question.trim()) return;

  if (predefinedQuestion) {
    questionInput.value = predefinedQuestion;
  }

  // Set up loading state
  answerBox.innerHTML = '<span class="thinking">Thinking<span class="dots"><span>.</span><span>.</span><span>.</span></span></span>';
  answerBox.classList.remove("muted");
  if (btn) { btn.disabled = true; btn.textContent = "Working…"; }

  const startTime = Date.now();
  let firstChunkReceived = false;

  try {
    await Api.askCopilot(collection, question, (chunk) => {
      if (!firstChunkReceived) {
        answerBox.innerHTML = ""; // Clear thinking indicator
        firstChunkReceived = true;
      }
      // Simple text append for now, can be upgraded to markdown later
      const span = document.createElement("span");
      span.textContent = chunk;
      answerBox.appendChild(span);
    });
    
    // Add time taken
    const timeTaken = ((Date.now() - startTime) / 1000).toFixed(1);
    const timeSpan = document.createElement("div");
    timeSpan.className = "time-taken muted";
    timeSpan.style.marginTop = "10px";
    timeSpan.style.fontSize = "0.85em";
    timeSpan.textContent = `Answer generated in ${timeTaken}s`;
    answerBox.appendChild(timeSpan);
    
  } catch (err) {
    answerBox.textContent = `Error: ${err.message}`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Ask Copilot"; }
  }
}
