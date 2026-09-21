const slides = document.querySelectorAll(".slide");
const progress = document.getElementById("progress");
let current = 0;

function show(index) {
  current = Math.max(0, Math.min(slides.length - 1, index));
  slides.forEach((slide, i) => slide.classList.toggle("active", i === current));
  progress.textContent = `${current + 1} / ${slides.length}`;
}

document.getElementById("prev").addEventListener("click", () => show(current - 1));
document.getElementById("next").addEventListener("click", () => show(current + 1));

window.addEventListener("keydown", (event) => {
  if (["ArrowRight", " ", "PageDown"].includes(event.key)) show(current + 1);
  if (["ArrowLeft", "PageUp"].includes(event.key)) show(current - 1);
});

show(0);
