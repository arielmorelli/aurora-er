# Documentation

Applies to every Markdown file: README, `CLAUDE.md`, ADRs, guidelines, history and the problem definition.

## Line breaks

- Never break a sentence or paragraph across lines. Each paragraph, list item and blockquote is written on a single line, however long; editors and renderers wrap it for display.
- Line breaks only separate blocks: paragraphs, list items, headings, table rows and lines inside code blocks.
- This keeps diffs readable (a changed sentence changes one line) and avoids re-wrapping whole paragraphs after an edit.

## Structure

- ADRs follow [`adr/template.md`](../adr/template.md).
- The history ([`history.md`](../history.md)) gets a new step for each piece of work, as bullets.
