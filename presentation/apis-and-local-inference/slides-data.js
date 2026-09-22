// Slide content for the deck, kept separate from rendering (app.js) and
// styling (style.css). Slide shapes:
//   { type: "title", title, byline, attribution }
//   { type: "section", title }            -- a divider slide between parts of the talk
//   { type: "content", title, items, cards }
// Each item in a list is either a plain string, or an object
// { text, children, chip } where `children` is a nested list (same shape,
// recursively) and `chip` renders a small pill-style link.
//
// One idea per slide: each "content" slide below covers a single point from
// the source deck rather than a whole dense bullet list, grouped into named
// sections with a divider slide in front of each group.

const SLIDES = [
  {
    type: "title",
    title: "APIs and Local Inference",
    byline: "Jane Adams",
    attribution: "Adapted from a talk by Andreas Werdich and Nathan Palmer",
  },

  // --- Motivation ---
  { type: "section", title: "Motivation: API vs Chatbot/GUI" },
  {
    type: "content",
    title: "Control and Reproducibility",
    items: [
      "Programmatic access: inference on large data sets",
      "Hyperparameter control (temp, top_p, num_completions, …)",
      "Structured outputs (e.g. for zero-shot text classification)",
      "Reproducibility, model versions, checkpoints",
    ],
  },
  {
    type: "content",
    title: "Operational Guarantees",
    items: ["Performance guarantees", "Security, privacy, compliance", "Cost control"],
  },

  // --- Local inference ---
  { type: "section", title: "Local Inference" },
  {
    type: "content",
    title: "What's an API, and When Do You Need One",
    items: ["What's an API", "When do I need one"],
  },
  {
    type: "content",
    title: "Examples",
    items: ["OpenAI, Azure OpenAI", "Anthropic", "Ollama, vLLM"],
  },
  {
    type: "content",
    title: "Local Inference Places",
    cards: [
      {
        callout: ["LOCAL? INFERENCE?", "GUI or API?"],
        heading: "Local inference places",
        items: ["Your laptop", "HMS HPC Clusters O2", "CCB servers"],
      },
    ],
  },

  // --- Model serving software ---
  { type: "section", title: "Model Serving Software" },
  {
    type: "content",
    title: "Ollama vs. vLLM",
    items: ["Ollama", "VLLM", 'On "bare metal" vs. container'],
  },
  {
    type: "content",
    title: "Setting Up a Model Server",
    cards: [
      {
        heading: "Setting up a model server",
        items: [
          "On your laptop for local inference",
          {
            text: "At HMS on the HPC cluster",
            chip: {
              label: "github.com/ccb-hms/LLMTools-HMS",
              href: "https://github.com/ccb-hms/LLMTools-HMS",
            },
          },
          "In the cloud",
        ],
      },
    ],
  },

  // --- Architecture of an AI inference stack ---
  { type: "section", title: "Architecture of an AI Inference Stack" },
  {
    type: "content",
    title: "The Full Stack",
    items: [
      { text: "Hardware (GPU, CPU)", children: ["ARM vs Intel"] },
      "OS loads device driver",
      {
        text: "SDKs on top of drivers",
        children: ["CUDA, cuDNN, TensorRT, …", '"bare metal"', "Containers"],
      },
      "Frameworks on top of SDKs (transformers, etc.)",
      "Open weight model",
      "Model serving software",
      "API",
      "Client",
    ],
  },
  {
    type: "content",
    title: "Hardware",
    items: [{ text: "GPU, CPU", children: ["ARM vs Intel"] }],
  },
  {
    type: "content",
    title: "OS Loads Device Driver",
  },
  {
    type: "content",
    title: "SDKs on Top of Drivers",
    items: ["CUDA, cuDNN, TensorRT, …", '"bare metal"', "Containers"],
  },
  {
    type: "content",
    title: "Frameworks on Top of SDKs",
    items: ["transformers, etc."],
  },
  {
    type: "content",
    title: "Open Weight Model",
  },
  {
    type: "content",
    title: "Model Serving Software",
  },
  {
    type: "content",
    title: "API",
  },
  {
    type: "content",
    title: "Client",
  },

  // --- Under the hood: containers, the forward pass, memory ---
  { type: "section", title: "Under the Hood" },
  {
    type: "content",
    title: "Containers",
    items: ["Docker", "Nvidia", "GitHub"],
  },
  {
    type: "content",
    title: "A Deeper Look at the Forward Pass (Inference)",
    items: [
      "Model weights loaded: disk → RAM → HBM",
      "The forward pass with attention",
    ],
  },
  {
    type: "content",
    title: "GPU Requirements",
    items: [
      "HBM is generally the limiting factor",
      "Multiple coprocessors can work together, NVLINK",
      "Can offload weights to system memory, with varying performance depending on platform",
    ],
  },
  {
    type: "content",
    title: "Implications of Context Window Size",
    items: [
      "Bigger window → more information attended to at inference time",
      "Bigger window needs more HBM / RAM",
      "Common max context window sizes, and real world interpretation (e.g., what can I fit in 128k tokens?)",
    ],
  },

  // --- Hardware guidance ---
  { type: "section", title: "Guidance for Local Hardware" },
  {
    type: "content",
    title: "Matching Problems to Hardware",
    items: ["What types of problems can we solve on various hardware"],
  },
  {
    type: "content",
    title: "Servers",
    items: [
      {
        text: "Intel / ARM servers with NVIDIA GPUs",
        children: ["DGX, Dell, Grace Hopper / Blackwell"],
      },
    ],
  },
  {
    type: "content",
    title: "Desktop Workstations",
    items: ["Intel with NVIDIA GPUs", "NVIDIA ARM", "Apple Silicon (Mac Studio)"],
  },
  {
    type: "content",
    title: "Hardware Options at HMS (O2, Longwood)",
  },

  // --- Hands-on demo ---
  { type: "section", title: "Today's Hands-On Demo" },
  {
    type: "content",
    title: "What You'll Run",
    items: [
      "A small open-weight model (Qwen2.5-1.5B) running entirely on your laptop, no GPU required",
      "Wrapped in an agentic tool loop that calls a real public bioinformatics API (GTEx)",
      "A browser UI that narrates every tool call live, as it actually happens",
    ],
  },
  {
    type: "content",
    title: "How It's Wired Together",
    items: [
      "Browser UI sends your question over a streamed connection (Server-Sent Events)",
      "Local model decides which tool to call, and in what order",
      {
        text: "Agent loop calls four atomic tools against GTEx",
        children: ["resolve_gene → fetch_gene_expression → summarize / plot"],
      },
      "Each step streams back to the browser the instant it's produced",
    ],
  },
  {
    type: "content",
    title: "What to Watch For",
    items: [
      "Constrained decoding (outlines) guarantees syntactically valid tool calls, not correct judgment",
      "MAX_STEPS caps runaway loops — a real safety mechanism, not a nicety",
      "Check the model's claims against the chart: it can name the wrong gene with total confidence",
    ],
  },

  // --- Resources ---
  { type: "section", title: "Resources for Your Next Steps" },
  {
    type: "content",
    title: "Where to Go From Here",
    items: ["Git repos maintained by CCB", "NVIDIA registry"],
  },
  {
    type: "content",
    title: "Reading and Further Study",
    items: [
      'Research papers, "Build a LLM from Scratch", etc.',
      "Pointers to helpful blog posts, etc.",
    ],
  },
];
