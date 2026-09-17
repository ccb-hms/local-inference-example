const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const chartEl = document.getElementById("chart");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function addMessage(kind, text) {
  const el = document.createElement("div");
  el.className = `message ${kind}`;
  if (kind === "observation" && text.includes("error:")) {
    el.classList.add("error");
  }
  if (kind === "api_call") {
    // A real, independently-checkable request URL - shown ellipsis-truncated
    // (full URL on hover/click) rather than wrapped, so it reads as a link,
    // not a paragraph. Built via DOM properties (not innerHTML) so nothing
    // in the URL - which is built from the model's own tool-call arguments -
    // can be interpreted as markup.
    const link = document.createElement("a");
    link.href = text;
    link.target = "_blank";
    link.rel = "noopener";
    link.title = text;
    link.textContent = text;
    // Belt-and-suspenders: some embedded webviews don't reliably honor
    // target="_blank" on its own. Explicitly open a new tab/window and
    // stop the default click from navigating this one - clicking this
    // link should never lose the conversation in the current tab.
    link.addEventListener("click", (event) => {
      event.preventDefault();
      window.open(text, "_blank", "noopener");
    });
    el.appendChild(link);
  } else {
    el.textContent = text;
  }
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

function setFormDisabled(disabled) {
  inputEl.disabled = disabled;
  formEl.querySelector("button").disabled = disabled;
}

async function sendMessage(message) {
  addMessage("user", message);
  setFormDisabled(true);
  const thinking = addMessage("action", "Thinking...");

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!resp.ok) {
      throw new Error(`server responded with ${resp.status}`);
    }
    const data = await resp.json();
    thinking.remove();

    // The backend already ran the whole agent loop - replay its steps with
    // a short pause between each so the chat reads as "live" narration
    // instead of a wall of text appearing all at once.
    for (const entry of data.transcript) {
      if (entry.kind === "final") continue; // shown separately, below
      addMessage(entry.kind, entry.text);
      await sleep(350);
    }
    addMessage("final", data.answer);

    if (data.chart) {
      chartEl.innerHTML = "";
      await vegaEmbed("#chart", data.chart, { actions: false });
    } else {
      chartEl.innerHTML = '<p class="chart-placeholder">(this answer didn\'t produce a chart)</p>';
    }
  } catch (err) {
    thinking.remove();
    addMessage("final", `Something went wrong: ${err.message}`);
  } finally {
    setFormDisabled(false);
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = inputEl.value.trim();
  if (!message) return;
  inputEl.value = "";
  sendMessage(message);
});
