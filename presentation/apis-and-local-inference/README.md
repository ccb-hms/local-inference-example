# APIs and Local Inference

A plain HTML/CSS/JS slide deck (no build step, no framework), based on the
original "APIs and Local Inference" talk by Andreas Werdich and Nathan
Palmer. This version is being adapted for delivery by Jane Adams.

Open `index.html` directly in a browser, or serve the folder:

```bash
python3 -m http.server -d presentation/apis-and-local-inference 8080
```

Use the arrow keys, spacebar, or Page Up/Down to move between slides (no
on-screen buttons &mdash; keyboard only). The current slide number is kept in
the URL hash (e.g. `#5`), so refreshing or sharing a link returns to the
same slide instead of resetting to the first one.

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

Slides come in three shapes: `type: "title"` (the opening slide),
`type: "section"` (a centered divider slide that introduces a part of the
talk, no body content), and `type: "content"` (a normal slide with a
heading plus `items` and/or `cards`). The deck deliberately keeps one idea
per content slide &mdash; e.g. each layer of the inference stack gets its own
slide rather than one dense bulleted overview &mdash; grouped under section
dividers by topic.

## Status

Content now mirrors the source deck in full (verbatim, no wording changes),
split across more, more-focused slides than the original 12, still pending
a pass to rework the material for this presenter and audience.
