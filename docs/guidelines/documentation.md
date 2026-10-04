# Documentation

Applies to every Markdown file: README, `CLAUDE.md`, ADRs, guidelines, history and the problem definition.

## Line breaks

- Never break a sentence or paragraph across lines. Each paragraph, list item and blockquote is written on a single line, however long; editors and renderers wrap it for display.
- Line breaks only separate blocks: paragraphs, list items, headings, table rows and lines inside code blocks.
- This keeps diffs readable (a changed sentence changes one line) and avoids re-wrapping whole paragraphs after an edit.

## Numbers that go stale

- Documents describing the current state (README, `CLAUDE.md`, guidelines, design documents, problem definition, architecture) never state a number that changes as the project evolves: counts (tests, files, modules), run times, sizes, versions, settings copied from code or config, or model results. Say how to get the number instead (e.g. "run `make test`"), or point to the code or config that defines it.
- Numbers fixed by the brief or the input data (the example in the brief, the data's date range, the battery parameters) are not stale and stay.
- Point-in-time records keep their numbers as written: ADRs, the history and the dated results in [`results.md`](../results.md), which also records the date and commit.

## Structure

- ADRs follow [`adr/template.md`](../adr/template.md).
- The history ([`history.md`](../history.md)) gets a new step for each piece of work, as bullets.
