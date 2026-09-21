// Renders SLIDES (slides-data.js) into #deck, then drives navigation.
// Templates below are the only place that knows about slide markup/CSS
// classes — slides-data.js stays pure content.

function renderList(items) {
  const ul = document.createElement("ul");
  for (const item of items) {
    const li = document.createElement("li");
    if (typeof item === "string") {
      li.textContent = item;
    } else {
      li.appendChild(document.createTextNode(item.text));
      if (item.chip) {
        const a = document.createElement("a");
        a.className = "chip";
        a.href = item.chip.href;
        a.textContent = item.chip.label;
        li.appendChild(a);
      }
      if (item.children) {
        li.appendChild(renderList(item.children));
      }
    }
    ul.appendChild(li);
  }
  return ul;
}

function renderCard(card) {
  const div = document.createElement("div");
  div.className = "card";

  if (card.callout) {
    const p = document.createElement("p");
    p.className = "callout";
    card.callout.forEach((line, i) => {
      if (i > 0) p.appendChild(document.createElement("br"));
      p.appendChild(document.createTextNode(line));
    });
    div.appendChild(p);
  }

  if (card.heading) {
    const h3 = document.createElement("h3");
    h3.textContent = card.heading;
    div.appendChild(h3);
  }

  div.appendChild(renderList(card.items));
  return div;
}

function renderTitleSlide(slide) {
  const section = document.createElement("section");
  section.className = "slide";

  const h1 = document.createElement("h1");
  h1.textContent = slide.title;
  section.appendChild(h1);

  if (slide.byline) {
    const p = document.createElement("p");
    p.className = "byline";
    p.textContent = slide.byline;
    section.appendChild(p);
  }

  if (slide.attribution) {
    const p = document.createElement("p");
    p.className = "attribution";
    p.textContent = slide.attribution;
    section.appendChild(p);
  }

  return section;
}

function renderContentSlide(slide) {
  const section = document.createElement("section");
  section.className = "slide";

  const h2 = document.createElement("h2");
  h2.textContent = slide.title;
  section.appendChild(h2);

  if (slide.items) {
    section.appendChild(renderList(slide.items));
  }

  if (slide.cards) {
    for (const card of slide.cards) {
      section.appendChild(renderCard(card));
    }
  }

  return section;
}

function renderSlide(slide) {
  return slide.type === "title" ? renderTitleSlide(slide) : renderContentSlide(slide);
}

const deck = document.getElementById("deck");
for (const slide of SLIDES) {
  deck.appendChild(renderSlide(slide));
}

const slideEls = document.querySelectorAll(".slide");
const progress = document.getElementById("progress");
let current = 0;

function show(index) {
  current = Math.max(0, Math.min(slideEls.length - 1, index));
  slideEls.forEach((slide, i) => slide.classList.toggle("active", i === current));
  progress.textContent = `${current + 1} / ${slideEls.length}`;
}

document.getElementById("prev").addEventListener("click", () => show(current - 1));
document.getElementById("next").addEventListener("click", () => show(current + 1));

window.addEventListener("keydown", (event) => {
  if (["ArrowRight", " ", "PageDown"].includes(event.key)) show(current + 1);
  if (["ArrowLeft", "PageUp"].includes(event.key)) show(current - 1);
});

show(0);
