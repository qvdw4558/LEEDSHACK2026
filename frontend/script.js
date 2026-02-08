const chatBody = document.getElementById("chatBody");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");

const tplUserMsg = document.getElementById("tplUserMsg");
const tplBotMsg  = document.getElementById("tplBotMsg");

// Extracted panel
const fromCityEl = document.getElementById("fromCity");
const toCityEl   = document.getElementById("toCity");
const shipDateEl = document.getElementById("shipDate");

// Conversation memory (sent to backend each turn)
const messages = [];

// Latest canonical shipment state
let shipmentState = {
  ship_from_city: null,
  ship_to_city: null,
  ship_date: null
};

function scrollToBottom() {
  chatBody.scrollTop = chatBody.scrollHeight;
}

function renderShipment() {
  fromCityEl.textContent = shipmentState.ship_from_city ?? "—";
  toCityEl.textContent   = shipmentState.ship_to_city ?? "—";
  shipDateEl.textContent = shipmentState.ship_date ?? "—";
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

async function callBackend(messagesSoFar) {
  const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: messagesSoFar })
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Backend error ${res.status}: ${txt}`);
  }

  return await res.json(); // { reply, shipment, (optional error) }
}

let inFlight = false;

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (inFlight) return;

  const text = chatInput.value.trim();
  if (!text) return;

  // record + render user
  messages.push({ role: "user", content: text });
  appendUser(text);
  chatInput.value = "";

  inFlight = true;
  chatInput.disabled = true;
  chatForm.querySelector("button[type='submit']").disabled = true;

  try {
    const result = await callBackend(messages);

    // render bot reply
    const reply = result.reply || "Temporary issue. Try again.";
    messages.push({ role: "assistant", content: reply });
    appendBot(reply);

    // update shipment state
    if (result.shipment) {
      shipmentState = {
        ship_from_city: result.shipment.ship_from_city ?? null,
        ship_to_city: result.shipment.ship_to_city ?? null,
        ship_date: result.shipment.ship_date ?? null
      };
      renderShipment();
    }

  } catch (err) {
    console.error(err);
    appendBot("Temporary connection issue. Send again.");
  } finally {
    inFlight = false;
    chatInput.disabled = false;
    chatForm.querySelector("button[type='submit']").disabled = false;
    chatInput.focus();
  }
});

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

// initial
renderShipment();
appendBot("Hey — tell me where you’re shipping from, where to, and what date.");
