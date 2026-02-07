// Minimal wiring: send -> append message -> scroll.
// Later: replace fakeBotReply() with a Gemini call.

const chatBody = document.getElementById("chatBody");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");

function scrollToBottom() {
  chatBody.scrollTop = chatBody.scrollHeight;
}

function createUserMessage(text) {
  const article = document.createElement("article");
  article.className = "msg msg-user";
  article.innerHTML = `
    <div class="bubble bubble-user">
      <p class="bubble-text"></p>
    </div>
  `;
  article.querySelector(".bubble-text").textContent = text;
  return article;
}

// Optional: placeholder bot reply so you can see the flow.
// Delete this when you wire Gemini in.
function createBotMessage(text) {
  const article = document.createElement("article");
  article.className = "msg msg-bot";
  article.innerHTML = `
    <div class="msg-avatar" aria-hidden="true">
      <div class="avatar small">
        <svg viewBox="0 0 64 64" width="18" height="18">
          <circle cx="32" cy="20" r="6" fill="currentColor" opacity="0.95"/>
          <rect x="14" y="24" width="36" height="26" rx="10" fill="currentColor" opacity="0.95"/>
          <rect x="10" y="28" width="44" height="22" rx="11" fill="white" opacity="0.25"/>
          <circle cx="26" cy="37" r="3" fill="white"/>
          <circle cx="38" cy="37" r="3" fill="white"/>
          <rect x="28" y="44" width="8" height="2.8" rx="1.4" fill="white" opacity="0.8"/>
          <rect x="31" y="7" width="2" height="8" rx="1" fill="currentColor" opacity="0.95"/>
        </svg>
      </div>
    </div>
    <div class="bubble bubble-bot">
      <p class="bubble-text"></p>
    </div>
  `;
  article.querySelector(".bubble-text").textContent = text;
  return article;
}

async function fakeBotReply(userText) {
  // Stub: this is exactly where your Gemini call will go later.
  // Return a string.
  return `Got it: "${userText}" (stub reply)`;
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const text = chatInput.value.trim();
  if (!text) return;

  // add user message
  chatBody.appendChild(createUserMessage(text));
  chatInput.value = "";
  scrollToBottom();

  // stub bot reply (remove later)
  const reply = await fakeBotReply(text);
  chatBody.appendChild(createBotMessage(reply));
  scrollToBottom();
});

// nice-to-have: Enter sends, Shift+Enter doesn't (input is single-line anyway)
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    // form submit will handle it; this just prevents accidental newline behavior
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

// initial scroll in case demo messages overflow
scrollToBottom();
