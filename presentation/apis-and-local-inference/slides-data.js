// Slide content for the deck, kept separate from rendering (app.js) and
// styling (style.css). Each item in a list is either a plain string, or an
// object { text, children, chip } where `children` is a nested list (same
// shape, recursively) and `chip` renders a small pill-style link.

const SLIDES = [
  {
    type: "title",
    title: "APIs and Local Inference",
    byline: "Jane Adams",
    attribution: "Adapted from a talk by Andreas Werdich and Nathan Palmer",
  },
  {
    type: "content",
    title: "Motivation: API vs Chatbot/GUI",
    items: [
      "Programmatic access: inference on large data sets",
      "Hyperparameter control (temp, top_p, num_completions, …)",
      "Structured outputs (e.g. for zero-shot text classification)",
      "Reproducibility, model versions, checkpoints",
      "Performance guarantees",
      "Security, privacy, compliance",
      "Cost control",
    ],
  },
  {
    type: "content",
    title: "Local inference",
    items: [
      "What's an API",
      "When do I need one",
      {
        text: "Examples",
        children: ["OpenAI, Azure OpenAI", "Anthropic", "Ollama, vLLM"],
      },
    ],
    cards: [
      {
        callout: ["LOCAL? INFERENCE?", "GUI or API?"],
        heading: "Local inference places",
        items: ["Your laptop", "HMS HPC Clusters O2", "CCB servers"],
      },
    ],
  },
  {
    type: "content",
    title: "Model Serving Software",
    items: ["Ollama", "VLLM", 'On "bare metal" vs. container'],
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
  {
    type: "content",
    title: "Architecture of an AI Inference Stack",
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
  {
    type: "content",
    title: "Guidance for Local Hardware",
    items: [
      "What types of problems can we solve on various hardware",
      {
        text: "Intel / ARM servers with NVIDIA GPUs",
        children: ["DGX, Dell, Grace Hopper / Blackwell"],
      },
      {
        text: "Desktop workstations",
        children: [
          "Intel with NVIDIA GPUs",
          "NVIDIA ARM",
          "Apple Silicon (Mac Studio)",
        ],
      },
    ],
  },
  {
    type: "content",
    title: "Hardware Options at HMS (O2, Longwood)",
  },
  {
    type: "content",
    title: "Resources for your next steps",
    items: [
      {
        text: "Pointers to:",
        children: [
          "Git repos maintained by CCB",
          "NVIDIA registry",
          {
            text: "Reading material for deeper dive",
            children: ['Research papers, "Build a LLM from Scratch", etc.'],
          },
          "Pointers to helpful blog posts, etc.",
        ],
      },
    ],
  },
];
