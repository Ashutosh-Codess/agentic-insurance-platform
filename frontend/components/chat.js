// Handles the copilot chat box on pages/copilot.html - sends a question,
// streams the answer into the page as it arrives.

async function sendCopilotQuestion() {
  const collection = document.getElementById("copilot-collection").value;
  const question = document.getElementById("copilot-question").value;
  const answerBox = document.getElementById("copilot-answer");
  const btn = document.getElementById("copilot-btn");

  if (!question.trim()) return;

  answerBox.textContent = "";
  answerBox.classList.remove("muted");
  if (btn) { btn.disabled = true; btn.textContent = "Thinking…"; }

  try {
    await Api.askCopilot(collection, question, (chunk) => {
      answerBox.textContent += chunk;
    });
  } catch (err) {
    answerBox.textContent = `Error: ${err.message}`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Ask Copilot"; }
  }
}
