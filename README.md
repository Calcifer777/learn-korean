# Learn Korean Toolkit 🇰🇷

An automated toolkit designed to transform Korean texts and drama subtitles into rich, context-aware learning materials. This project helps you master Korean by extracting vocabulary, generating LLM-powered etymology (Hanja), and creating beautiful Anki flashcard decks.

## 🚀 Quick Start

### Prerequisites
- [Python 3.13+](https://www.python.org/)
- [uv](https://github.com/astral-sh/uv) (Fast Python package manager)
- A [Gemini API Key](https://aistudio.google.com/app/apikey) (for context-aware translations)
- An [ElevenLabs API Key](https://elevenlabs.io/) (for high-quality TTS)

### Setup
1. Clone the repository and install dependencies:
   ```bash
   uv sync
   ```
2. Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_key_here
   ELEVENLABS_API_KEY=your_key_here
   ```

---

## 🛠 Command Reference

The toolkit is accessible via `uv run learn-korean`.

### 1. End-to-End Pipeline (`process-text`)
The primary command for generating a study deck from a text file. It extracts unique words, identifies idiomatic phrases, translates them with Gemini, and builds an Anki deck.

```bash
uv run learn-korean process-text \
  --input stories/001.md \
  --output-csv outputs/001.csv \
  --output-anki outputs/001.apkg \
  --deck-name "Story 01: Pali-Pali" \
  --phrases
```
- `--phrases`: Automatically mines 2-3 word idiomatic "blocks" (collocations).
- `--no-llm`: Disables Gemini and uses basic Google Translation (not recommended).
- `--dev`: Process only the first 5 items (useful for testing).
- `--exclude-common`: Filters out the top 1,000 most common Korean words.

### 2. Mining Drama Subtitles (`mine-drama`)
Extracts vocabulary from `.lrc` or `.srt` files based on frequency.

```bash
uv run learn-korean mine-drama \
  --input subtitles.lrc \
  --output vocab.csv \
  --min-freq 2
```

### 3. Text-to-Speech (`tts`)
Generates high-quality audio using ElevenLabs' multilingual v2 model.

```bash
uv run learn-korean tts \
  --voice "Bella" \
  --input text.txt \
  --output audio.mp3
```

### 4. Audio Alignment (`align` / `align-all`)
Force-aligns text to audio to generate synchronized `.lrc` subtitle files using `stable-ts`.

```bash
# Single file
uv run learn-korean align --audio voice.mp3 --text script.txt --output synced.lrc

# Bulk align a directory
uv run learn-korean align-all --dir resources/lessons/
```

---

## 📇 Anki Card Structure

The toolkit generates cards using the **"Context-Aware Korean Vocab v3"** model, styled with the **Catppuccin Frappé** theme.

Each card includes:
- **Korean Word/Phrase**: Large, bolded text.
- **Definition**: Contextually appropriate English meaning.
- **Hanja Etymology**: Literal root breakdowns (e.g., `기 (steam) + 차 (car)`).
- **Example Sentence**: The original sentence where the word was found.
- **Sentence Translation**: English translation of the context.

---

## 🧪 Development & Testing

Run the test suite to verify extraction and Anki logic:
```bash
uv run pytest
```

Check code quality and types:
```bash
prek run --all-files
```

---

## 📜 License
This project is for personal educational use.
