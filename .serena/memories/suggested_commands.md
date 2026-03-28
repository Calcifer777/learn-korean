# Suggested Commands

The CLI tool is run using `uv`. The primary entrypoint is `learn-korean`.

**Core Commands:**

- `uv run learn-korean process-text --input <file> --output-csv <csv> --output-anki <apkg> --deck-name <name> --llm` (End-to-end extraction, translation, and Anki deck generation)
- `uv run learn-korean extract-vocab --input <file> --output <csv>`
- `uv run learn-korean mine-drama --input <file> --output <csv>`
- `uv run learn-korean translate-vocab --input <csv> --output <csv> --llm`
- `uv run learn-korean anki-deck --input <file_or_csv> --output <apkg> --name <name>`

**Testing/Dev:**

- Use the `--dev` flag on `process-text`, `extract-vocab`, or `mine-drama` to limit processing to the first 5 items for rapid testing.
- `uv run pytest` (if tests are added).
