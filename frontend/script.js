const chatBody = document.getElementById("chatBody");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");

const tplUserMsg = document.getElementById("tplUserMsg");
const tplBotMsg  = document.getElementById("tplBotMsg");

// Debug panel (optional)
const fromCityEl = document.getElementById("fromCity");
const toCityEl   = document.getElementById("toCity");
const shipTimeEl = document.getElementById("shipTime");

// 1) Conversation memory for Gemini later
// Keep it simple: role + content
const messages = [];

// 2) Extracted variables state (what you'll pass to python backend)
let extractedState = {
  ship_from_city: null,
  ship_to_city: null,
  ship_time: null
};

function scrollToBottom() {
  chatBody.scrollTop = chatBody.scrollHeight;
}

function renderState() {
  if (!fromCityEl) return; // panel optional
  fromCityEl.textContent = extractedState.ship_from_city ?? "—";
  toCityEl.textContent   = extractedState.ship_to_city ?? "—";
  shipTimeEl.textContent = extractedState.ship_time ?? "—";
}

function appendUser(text) {
  const node = tplUserMsg.content.cloneNode(true);
  node.querySelector(".bubble-text").textContent = text;
  chatBody.appendChild(node);
  scrollToBottom();
}

function appendBot(text) {
  const node = tplBotMsg.content.cloneNode(true);
  node.querySelector(".bubble-text").textContent = text;
  chatBody.appendChild(node);
  scrollToBottom();
}

/**
 * Placeholder backend call.
 *
 * Later you will replace this with:
 *   fetch("/chat", { method:"POST", headers:{...}, body: JSON.stringify({ messages, state }) })
 *
 * Expected return shape:
 *   { reply: string, state: { ship_from_city, ship_to_city, ship_time } }
 */
async function callBackend(messagesSoFar, currentState) {
 const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: messagesSoFar, state: currentState })
  });

  if (!res.ok) throw new Error("Backend error");
  return await res.json(); // { reply, state }
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const text = chatInput.value.trim();
  if (!text) return;

  // Record user message
  messages.push({ role: "user", content: text });

  // Show user message immediately
  appendUser(text);
  chatInput.value = "";

  // Disable input while "backend" runs
  chatInput.disabled = true;
  chatForm.querySelector("button[type='submit']").disabled = true;

  try {
    // Backend returns bot reply + updated extracted variables
    const result = await callBackend(messages, extractedState);

    // Record + render bot message
    messages.push({ role: "assistant", content: result.reply });
    appendBot(result.reply);

    // Update extracted state
    extractedState = result.state;
    renderState();

    // In the real version, you also POST extractedState to your python processing
    // or include it in the same /chat response like above.
  } catch (err) {
    appendBot("Something went wrong. Try again.");
    console.error(err);
  } finally {
    chatInput.disabled = false;
    chatForm.querySelector("button[type='submit']").disabled = false;
    chatInput.focus();
  }
});

// nice: submit on Enter
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

// initial render
renderState();
appendBot("Hey — tell me where you’re shipping from, where to, and when.");
