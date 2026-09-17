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

function sendMessage(message) {
  addMessage("user", message);
  setFormDisabled(true);
  const thinking = addMessage("action", "Thinking...");
  let thinkingRemoved = false;
  let sawChart = false;

  // Real streaming, not a replay: each "step" event is pushed by the
  // server the instant run_agent_stream produces it, so a bubble appears
  // exactly when that step actually happens, not after the whole run
  // finishes and gets faked into looking live.
  const source = new EventSource(`/api/chat/stream?message=${encodeURIComponent(message)}`);

  const finish = () => {
    source.close();
    if (!sawChart) {
      chartEl.innerHTML = '<p class="chart-placeholder">(this answer didn\'t produce a chart)</p>';
    }
    setFormDisabled(false);
    inputEl.focus();
  };

  source.addEventListener("step", (event) => {
    if (!thinkingRemoved) {
      thinking.remove();
      thinkingRemoved = true;
    }
    const entry = JSON.parse(event.data);
    addMessage(entry.kind, entry.text, entry.detail);
    if (entry.detail) {
      showDetail(entry.kind, entry.detail);
    }
    if (entry.chart) {
      sawChart = true;
      chartEl.innerHTML = "";
      vegaEmbed("#chart", entry.chart, { actions: false });
    }
  });

  source.addEventListener("done", finish);

  source.onerror = () => {
    if (!thinkingRemoved) {
      thinking.remove();
    }
    addMessage("final", "Something went wrong talking to the server.");
    finish();
  };
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = inputEl.value.trim();
  if (!message) return;
  inputEl.value = "";
  sendMessage(message);
});
