# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                  # install dependencies
uv run pytest            # run tests
uv run pytest tests/test_translator.py  # run a single test file
prek run --all-files     # lint + type-check (ruff + pyrefly)
```

The toolkit CLI entry point:
```bash
uv run learn-korean <command> [options]
```

Use `--dev` on `process-text`, `extract-vocab`, or `mine-drama` to limit processing to 5 items for fast iteration.

Use `--translator {claude,gemini,simple}` (default: `claude`) on `process-text`, `translate-vocab`, and `anki-deck` to select the translation backend.

## Architecture

The package lives in `src/learn_korean/`. The CLI is defined in `__main__.py` using `argparse` with subcommands; all subcommand logic is delegated to the four modules below.

**`parser.py`** — text → word list
Uses `kiwipiepy` (Kiwi morphological analyzer) to tokenize Korean text, extract lemmas with POS tags (NNG/NNP/NNB → Noun, VV → Verb, VA → Adjective, MAG/MAJ → Adverb), and attach the source sentence as context. Verbs/adjectives get `다` appended to form dictionary entries. Returns `list[dict[str, str]]` with keys: `Korean`, `Part of Speech`, `Example Sentence`, `English`, `Sentence Translation`, `Etymology`.

**`miner.py`** — subtitle file → frequency-filtered word list
Parses `.lrc` or `.srt` files (stripping timestamps, HTML tags, speaker names), tokenizes with Kiwi, counts lemma frequency, and returns words above `--min-freq`. Shares `POS_MAP` with `parser.py`.

**`translator_claude.py`** — word list → translated word list (default backend)
`translate_with_claude` batches 30 words at a time, sends them to `claude-sonnet-4-6` with sentence context, and merges JSON responses back into the word dicts. `extract_phrases_with_claude` uses a separate prompt to extract 2–3 word idiomatic blocks from raw text. Both skip already-translated entries.

**`translator_llm.py`** — same interface backed by `gemini-2.5-flash` (use `--translator gemini`).

**`anki_utils.py`** — word list → `.apkg` deck
Uses `genanki` to build a bidirectional deck (Korean→English and English→Korean) with the **"Context-Aware Korean Vocab v3"** model, styled with Catppuccin Frappé. Deck and note IDs are stable (SHA-256 hashed) so re-importing doesn't create duplicates in Anki.

## Data flow for `process-text`

```
text file → parser.process_text_file()
          → translator_llm.extract_phrases_with_gemini()  (if --phrases)
          → translator_llm.translate_with_gemini()        (if --llm)
          → parser.save_vocab_to_csv()
          → anki_utils.generate_anki_deck()
```

## Resources layout

```
resources/
  vocab/1k.csv          # top-1000 common words exclusion list
  stories/              # source texts by series (how-to-study-korean, TTMIK, etc.)
  yeoeun/lessons/       # per-lesson audio + LRC files
```

Each lesson series folder typically contains: `NNN.kr.md` (Korean text), `NNN.mp3` (audio), `NNN.lrc` (synchronized subtitles), `NNN.words.csv` + `NNN.apkg` (output).

## Manual Anki deck creation (no API key)

When no translator API key is available, build the deck by hand from vocabulary/idioms already covered in a reading session, instead of running `process-text` (which requires a translator call):

1. Author `NNN.words.csv` and `NNN.idioms.csv` for the story directly with Python's `csv` module, matching `load_vocab_from_csv`'s column order exactly: `Korean,Part of Speech,Example Sentence,English,Sentence Translation,Etymology`.
   - Always fill in `Etymology`, never leave it blank. For Sino-Korean words, give the hanja breakdown (e.g. 과대평가하다 = 過 excess + 大 big + 評價 evaluation). For native Korean words (no hanja root), note cognates/derivations instead (e.g. 기울다 → 기울이다, 기울기, 기울어지다).
2. Combine both into `NNN.csv` (same column order, idioms/phrases appended after words).
3. Generate the deck:
   ```bash
   n=NNN
   uv run python -m learn_korean anki-deck --input resources/stories/<series>/$n.csv --name "<Series Name> - $n" --output resources/stories/<series>/$n.apkg
   ```
   Note: `n=NNN` is bash/zsh syntax. In fish, use `set n NNN` instead.

Always invoke Python as `uv run python3 ...` (or `uv run <entry point>`), never the bare `python3` binary — this project manages its env with `uv`.

## Environment

```
GEMINI_API_KEY=...        # required for LLM translation (default translator)
ELEVENLABS_API_KEY=...    # required for tts / list-voices / sample commands
ANTHROPIC_API_KEY=...     # required if using Claude as translator
```
