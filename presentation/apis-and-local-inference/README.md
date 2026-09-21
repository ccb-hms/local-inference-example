# APIs and Local Inference

A plain HTML/CSS/JS slide deck (no build step, no framework), based on the
original "APIs and Local Inference" talk by Andreas Werdich and Nathan
Palmer. This version is being adapted for delivery by Jane Adams.

Open `index.html` directly in a browser, or serve the folder:

```bash
python3 -m http.server -d presentation/apis-and-local-inference 8080
```

Use the on-screen arrows, arrow keys, or Page Up/Down to move between
slides.

## Structure

- `slides-data.js` &mdash; slide content only (titles, bullet lists, card
  callouts). Edit this file to change wording or add/remove/reorder slides.
- `app.js` &mdash; renders `slides-data.js` into the page and drives
  navigation. Shouldn't need changes for ordinary content edits.
- `style.css` &mdash; visual styling (cards, chips, transitions, light/dark).
- `index.html` &mdash; a minimal shell; it just loads the two scripts above.

Each item in a `slides-data.js` list is either a plain string, or an object
`{ text, children, chip }`, where `children` is a nested list (same shape)
and `chip` renders a small pill-style link. See the file for examples.

## Status

Content now mirrors the source deck in full (verbatim, including its
nested bullet structure), still pending a pass to rework the material for
this presenter and audience.
