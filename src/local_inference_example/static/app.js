const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const chartEl = document.getElementById("chart");
const detailPanelEl = document.getElementById("detail-panel");
const detailLabelEl = document.getElementById("detail-label");
const detailBodyEl = document.getElementById("detail-body");

const DETAIL_LABELS = {
  action: "Code being called",
  api_call: "API request",
  observation: "Data returned",
  final: "Model's final step",
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Shows one step's detail (code / API request / data) in the panel below
// the chart. Called both live, as each step streams in, and on demand
// when an earlier bubble is clicked - same function either way, so the
// panel always matches whatever's currently "active."
function showDetail(kind, detail) {
  if (!detail) return;
  detailPanelEl.className = `detail-panel kind-${kind}`;
  detailLabelEl.textContent = DETAIL_LABELS[kind] || "Details";
  const code = document.createElement("code");
  code.className = `language-${detail.language}`;
  code.textContent = detail.content;
  detailBodyEl.innerHTML = "";
  detailBodyEl.appendChild(code);
  if (window.hljs) {
    window.hljs.highlightElement(code);
  }
}

function addMessage(kind, text, detail) {
  const el = document.createElement("div");
  el.className = `message ${kind}`;
  if (kind === "observation" && text.includes("error:")) {
    el.classList.add("error");
  }
  el.textContent = text;
  if (kind === "api_call") {
    // Ellipsis-truncated (see .message.api_call in style.css) - the full
    // URL is on hover, and broken down in full in the detail panel below.
    // Deliberately not a link: clicking opens that panel instead of
    // navigating away to the raw GTEx page.
    el.title = text;
  } else if (detail) {
    el.title = "Click to inspect this step";
  }
  if (detail) {
    el.classList.add("has-detail");
    el.addEventListener("click", () => showDetail(kind, detail));
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
    // instead of a wall of text appearing all at once. The detail panel
    // tracks along: each step with a detail payload becomes the active one
    // as it's added, then stays there until either the next detail-bearing
    // step arrives or the user clicks an earlier bubble.
    for (const entry of data.transcript) {
      if (entry.kind === "final") continue; // shown separately, below
      addMessage(entry.kind, entry.text, entry.detail);
      if (entry.detail) {
        showDetail(entry.kind, entry.detail);
      }
      await sleep(350);
    }
    const finalEntry = data.transcript.find((entry) => entry.kind === "final");
    addMessage("final", data.answer, finalEntry ? finalEntry.detail : null);
    if (finalEntry && finalEntry.detail) {
      showDetail("final", finalEntry.detail);
    }

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
