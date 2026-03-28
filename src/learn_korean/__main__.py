import argparse
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from playsound3 import playsound
import stable_whisper
from tqdm import tqdm

# New imports
from .parser import (
    process_text_file,
    translate_words_simple,
    save_vocab_to_csv,
    load_vocab_from_csv,
)
from .anki_utils import generate_anki_deck
from .translator_llm import translate_with_gemini
from .miner import mine_subtitles

# Load environment variables from .env if present
load_dotenv()

CACHE_DIR = Path.home() / ".cache" / "elevenlabs" / "previews"


def get_preview_path(name: str) -> Path:
    """Returns a safe file path for a given voice name or ID."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join([c for c in name if c.isalnum() or c in " -_"]).strip()
    return CACHE_DIR / f"{safe_name}.mp3"


def play_audio(path: Path) -> None:
    """Plays the audio file using playsound3."""
    try:
        print(f"Playing sample...")
        playsound(str(path))
    except Exception as e:
        print(f"Warning: Could not play audio using playsound3: {e}", file=sys.stderr)
        print(f"The file is saved at: {path}", file=sys.stderr)


def resolve_voice_id(client: ElevenLabs, voice_input: str) -> str:
    """
    Tries to find a valid voice_id from a name or ID string.
    Prioritizes saved voices to avoid library payment restrictions.
    """
    try:
        saved = client.voices.get_all()
        for v in saved.voices:
            if v.name.lower() == voice_input.lower():
                print(f"Resolved name '{voice_input}' to saved voice ID '{v.voice_id}'")
                return v.voice_id
    except Exception:
        pass

    try:
        voice = client.voices.get(voice_id=voice_input)
        return voice.voice_id
    except Exception:
        pass

    try:
        shared = client.voices.get_shared(search=voice_input)
        if shared.voices:
            print(
                f"Resolved name '{voice_input}' to shared library voice ID '{shared.voices[0].voice_id}'"
            )
            return shared.voices[0].voice_id
    except Exception:
        pass

    return voice_input


def list_voices(
    client: ElevenLabs,
    language: str | None = None,
    shared: bool = False,
) -> None:
    try:
        if shared:
            response = (
                client.voices.get_shared(language=language)
                if language
                else client.voices.get_shared()
            )
            print(
                f"Available Shared Voices{' (language: ' + language + ')' if language else ''}:"
            )
            if not response.voices:
                print("No shared voices found.")
                return

            for voice in response.voices:
                print(
                    f"- {voice.name} (ID: {voice.voice_id}) [Category: {voice.category}]"
                )
        else:
            response = client.voices.get_all()
            print(
                f"Your Saved/Premade Voices{' (filtered by ' + language + ')' if language else ''}:"
            )
            found = False
            for voice in response.voices:
                labels = voice.labels or {}
                fine_tuning_lang = (
                    getattr(voice.fine_tuning, "language", None)
                    if voice.fine_tuning
                    else None
                )

                matches_label = (
                    any(language.lower() in str(val).lower() for val in labels.values())
                    if language
                    else True
                )
                matches_ft = (
                    (language.lower() in fine_tuning_lang.lower())
                    if language and fine_tuning_lang
                    else False
                )

                if not language or matches_label or matches_ft:
                    found = True
                    label_str = f" [Labels: {labels}]" if labels else ""
                    category = getattr(voice, "category", "unknown")
                    print(
                        f"- {voice.name} (ID: {voice.voice_id}) [Category: {category}]{label_str}"
                    )

            if not found:
                print("No matching voices found in your account.")
    except Exception as e:
        print(f"Error listing voices: {e}", file=sys.stderr)
        sys.exit(1)


def download_sample(
    client: ElevenLabs, resolved_id: str, voice_input: str
) -> Path | None:
    try:
        target_path = get_preview_path(voice_input)
        if target_path.exists():
            print(f"Using cached sample: {target_path}")
            return target_path

        print(f"Fetching metadata for voice ID '{resolved_id}'...")
        preview_url = None
        voice_name = "Unknown Voice"

        try:
            voice = client.voices.get(voice_id=resolved_id)
            preview_url = getattr(voice, "preview_url", None)
            voice_name = voice.name
        except Exception:
            pass

        if not preview_url:
            shared_response = client.voices.get_shared(search=resolved_id)
            if shared_response.voices:
                preview_url = getattr(shared_response.voices[0], "preview_url", None)
                voice_name = shared_response.voices[0].name

        if not preview_url:
            print(
                f"Error: Could not locate a preview URL for voice ID '{resolved_id}'."
            )
            return None

        actual_name_path = get_preview_path(voice_name)

        print(f"Downloading sample for '{voice_name}' from: {preview_url}")
        req = urllib.request.Request(preview_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            data = response.read()

            with open(target_path, "wb") as out_file:
                out_file.write(data)

            if target_path != actual_name_path and not actual_name_path.exists():
                with open(actual_name_path, "wb") as out_file:
                    out_file.write(data)

        print(f"Successfully saved to {target_path}")
        return target_path
    except Exception as e:
        print(f"Error downloading sample: {e}", file=sys.stderr)
        return None


def generate_tts(
    client: ElevenLabs,
    resolved_id: str,
    input_file: str,
    output_file: str,
) -> None:
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            text: str = f.read()

        print(f"Generating audio for '{input_file}' using voice ID '{resolved_id}'...")
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=resolved_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        with open(output_file, "wb") as f:
            if isinstance(audio, (Iterator, list)):
                for chunk in audio:
                    if chunk:
                        f.write(chunk)
            else:
                f.write(audio)

        print(f"Successfully saved TTS output to '{output_file}'")
    except Exception as e:
        print(f"Error generating TTS: {e}", file=sys.stderr)
        sys.exit(1)


def format_timestamp(seconds: float) -> str:
    """Format seconds into LRC timestamp format: [MM:SS.xx]"""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"[{minutes:02d}:{remaining_seconds:05.2f}]"


def _process_alignment(
    model,
    audio_path: str,
    text_path: str,
    output_path: str,
    language: str,
    offset_ms: int,
) -> None:
    """Core logic to read, clean, align, and save subtitles."""
    # Read and clean the text file
    with open(text_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Strip existing LRC timestamps like [00:00.00] if they exist
    clean_text = re.sub(r"\[\d{2}:\d{2}\.\d{2}\]", "", raw_text)
    # Collapse multiple newlines/spaces
    clean_text = re.sub(r"\n+", " ", clean_text).strip()

    if not clean_text:
        raise ValueError(
            f"The text file '{text_path}' appears to be empty after cleaning."
        )

    print(
        f"Aligning '{os.path.basename(audio_path)}' to the text (this might take a moment)..."
    )
    result = model.align(audio_path, clean_text, language=language)

    offset_seconds = offset_ms / 1000.0
    print(
        f"Writing synchronized subtitles to '{os.path.basename(output_path)}' with a {offset_ms}ms offset..."
    )
    with open(output_path, "w", encoding="utf-8") as f:
        for segment in result.segments:
            # Apply offset and ensure time is not negative
            synced_start = max(0, segment.start + offset_seconds)
            timestamp = format_timestamp(synced_start)
            f.write(f"{timestamp} {segment.text.strip()}\n")


def align_audio_text(
    audio_file: str,
    text_file: str,
    output_file: str,
    language: str = "ko",
    offset_ms: int = -200,
) -> None:
    """Aligns audio with text using stable-ts and faster-whisper, generating an LRC file."""
    try:
        print(f"Loading faster-whisper 'base' model via stable-ts...")
        # Use compute_type='int8' to ensure it runs comfortably on most machines
        model = stable_whisper.load_faster_whisper("base", compute_type="int8")

        _process_alignment(
            model, audio_file, text_file, output_file, language, offset_ms
        )

        print("Alignment complete! ✨")

    except Exception as e:
        print(f"Error during alignment: {e}", file=sys.stderr)
        sys.exit(1)


def align_all_audio_text(
    directory: str, language: str = "ko", offset_ms: int = -200
) -> None:
    """Aligns all .mp3 and .lrc pairs in a directory."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: '{directory}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    mp3_files = sorted(dir_path.glob("*.mp3"))
    if not mp3_files:
        print(f"No .mp3 files found in '{directory}'.")
        return

    print(f"Found {len(mp3_files)} .mp3 files. Loading faster-whisper 'base' model...")
    try:
        model = stable_whisper.load_faster_whisper("base", compute_type="int8")
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        sys.exit(1)

    for audio_path in tqdm(mp3_files, desc="Aligning audio files", unit="file"):
        lrc_path = audio_path.with_suffix(".lrc")
        if not lrc_path.exists():
            # Using tqdm.write to avoid interfering with progress bar
            tqdm.write(f"Skipping '{audio_path.name}': No matching .lrc file found.")
            continue

        try:
            _process_alignment(
                model,
                str(audio_path),
                str(lrc_path),
                str(lrc_path),
                language,
                offset_ms,
            )
        except Exception as e:
            tqdm.write(f"Error processing '{audio_path.name}': {e}")

    print("\nBulk alignment complete! ✨")


def load_exclusion_list(exclude_csv: str | None) -> set[str]:
    """Helper to load a set of Korean words from a CSV file."""
    known_words: set[str] = set()
    if not exclude_csv:
        return known_words

    try:
        import pandas as pd

        df_known = pd.read_csv(exclude_csv)
        if "Korean" in df_known.columns:
            known_words = set(df_known["Korean"].astype(str).tolist())
    except Exception as e:
        print(f"Warning: Could not load exclusion list {exclude_csv}: {e}")
    return known_words


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ElevenLabs TTS & Subtitle Alignment Tool"
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # Command: Process Text (End-to-End Workflow)
    process_parser = subparsers.add_parser(
        "process-text", help="Extract, translate, and generate an Anki deck in one go"
    )
    process_parser.add_argument(
        "--input", required=True, help="Path to the input text file"
    )
    process_parser.add_argument(
        "--output-csv", required=True, help="Path to the output CSV file"
    )
    process_parser.add_argument(
        "--output-anki", required=True, help="Path to the output .apkg file"
    )
    process_parser.add_argument(
        "--deck-name", required=True, help="Name of the deck inside Anki"
    )
    process_parser.add_argument(
        "--exclude", help="Optional CSV file of known words to exclude"
    )
    process_parser.add_argument(
        "--exclude-common", action="store_true", help="Automatically exclude most common words (1k.csv)"
    )
    process_parser.add_argument(
        "--llm", action="store_true", help="Use Gemini LLM for context-aware translation"
    )
    process_parser.add_argument(
        "--dev", action="store_true", help="Development mode: process only a few items for testing"
    )

    # Command: Extract Vocab
    extract_parser = subparsers.add_parser(
        "extract-vocab", help="Extract unique Korean words from text and save to CSV"
    )
    extract_parser.add_argument(
        "--input", required=True, help="Path to the input text file"
    )
    extract_parser.add_argument(
        "--output", required=True, help="Path to the output CSV file"
    )
    extract_parser.add_argument(
        "--exclude", help="Optional CSV file of known words to exclude"
    )
    extract_parser.add_argument(
        "--exclude-common",
        action="store_true",
        help="Automatically exclude most common words (1k.csv)",
    )
    extract_parser.add_argument(
        "--dev", action="store_true", help="Development mode: process only a few items for testing"
    )

    # Command: Mine Drama
    mine_parser = subparsers.add_parser(
        "mine-drama", help="Mine unique Korean words from drama subtitles (.lrc)"
    )
    mine_parser.add_argument(
        "--input", required=True, help="Path to the input subtitle file (.lrc)"
    )
    mine_parser.add_argument(
        "--output", required=True, help="Path to the output CSV file"
    )
    mine_parser.add_argument(
        "--min-freq",
        type=int,
        default=2,
        help="Minimum occurrences of a word (default: 2)",
    )
    mine_parser.add_argument(
        "--exclude", help="Optional CSV file of known words to exclude"
    )
    mine_parser.add_argument(
        "--exclude-common",
        action="store_true",
        help="Automatically exclude most common words (1k.csv)",
    )
    mine_parser.add_argument(
        "--dev", action="store_true", help="Development mode: process only a few items for testing"
    )

    # Command: Translate Vocab
    translate_parser = subparsers.add_parser(
        "translate-vocab", help="Translate words in a CSV file"
    )
    translate_parser.add_argument(
        "--input", required=True, help="Path to the input CSV file"
    )
    translate_parser.add_argument(
        "--output", required=True, help="Path to save the translated CSV file"
    )
    translate_parser.add_argument(
        "--llm",
        action="store_true",
        help="Use Gemini LLM for context-aware translation",
    )

    # Command: Anki Deck
    anki_parser = subparsers.add_parser(
        "anki-deck", help="Create an Anki deck from a Korean text or CSV file"
    )
    anki_parser.add_argument(
        "--input", required=True, help="Path to the input text or CSV file"
    )
    anki_parser.add_argument(
        "--output", required=True, help="Path to the output .apkg file"
    )
    anki_parser.add_argument(
        "--name", default="Korean Vocabulary", help="Name of the deck inside Anki"
    )
    anki_parser.add_argument(
        "--llm", action="store_true", help="Use Gemini LLM (if input is text)"
    )

    # Command: List voices
    list_parser = subparsers.add_parser(
        "list-voices", help="List all available ElevenLabs voices"
    )
    list_parser.add_argument(
        "--language",
        help="Filter voices by language/accent label (e.g., 'ko' for Korean)",
    )
    list_parser.add_argument(
        "--shared",
        action="store_true",
        help="Search the public library of shared voices instead of saved voices",
    )

    # Command: Sample
    sample_parser = subparsers.add_parser(
        "sample", help="Download, save, and play a sample audio for a voice"
    )
    sample_parser.add_argument("--voice", required=True, help="Voice Name or Voice ID")

    # Command: TTS
    tts_parser = subparsers.add_parser("tts", help="Generate an MP3 from a text file")
    tts_parser.add_argument("--voice", required=True, help="Voice Name or Voice ID")
    tts_parser.add_argument(
        "--input", required=True, help="Path to the input text file"
    )
    tts_parser.add_argument(
        "--output", required=True, help="Path to the output MP3 file"
    )

    # Command: Align
    align_parser = subparsers.add_parser(
        "align", help="Force-align text to an audio file using stable-ts"
    )
    align_parser.add_argument(
        "--audio", required=True, help="Path to the input MP3 file"
    )
    align_parser.add_argument(
        "--text", required=True, help="Path to the input text or broken LRC file"
    )
    align_parser.add_argument(
        "--output", required=True, help="Path to the output synced LRC file"
    )
    align_parser.add_argument(
        "--language", default="ko", help="Language code of the audio (default: ko)"
    )
    align_parser.add_argument(
        "--offset",
        type=int,
        default=-200,
        help="Offset in milliseconds to shift timestamps (default: -200)",
    )

    # Command: Align All
    align_all_parser = subparsers.add_parser(
        "align-all", help="Force-align all MP3/LRC pairs in a directory using stable-ts"
    )
    align_all_parser.add_argument(
        "--dir",
        required=True,
        help="Path to the directory containing MP3 and LRC files",
    )
    align_all_parser.add_argument(
        "--language", default="ko", help="Language code of the audio (default: ko)"
    )
    align_all_parser.add_argument(
        "--offset",
        type=int,
        default=-200,
        help="Offset in milliseconds to shift timestamps (default: -200)",
    )

    args = parser.parse_args()

    if args.command == "process-text":
        exclude_set = set()
        if args.exclude:
            exclude_set.update(load_exclusion_list(args.exclude))
        if args.exclude_common:
            common_path = (Path.cwd() / "resources" / "vocab" / "1k.csv").as_posix()
            if os.path.exists(common_path):
                exclude_set.update(load_exclusion_list(common_path))
            else:
                print(f"Warning: Common words file '{common_path}' not found.")

        print(f"Step 1/3: Extracting vocabulary from {args.input}...")
        words = process_text_file(args.input, exclude_set=exclude_set)
        if args.dev:
            print(f"Dev mode: limiting extraction to first 5 words.")
            words = words[:5]

        print("Step 2/3: Translating and extracting etymology...")
        if args.llm:
            words = translate_with_gemini(words)
        else:
            words = translate_words_simple(words)

        save_vocab_to_csv(words, args.output_csv)

        print(f"Step 3/3: Generating Anki deck ({args.deck_name})...")
        generate_anki_deck(words, args.output_anki, args.deck_name)
        return

    elif args.command == "extract-vocab":
        exclude_set = set()
        if args.exclude:
            exclude_set.update(load_exclusion_list(args.exclude))
        if args.exclude_common:
            common_path = (Path.cwd() / "resources" / "vocab" / "1k.csv").as_posix()
            if os.path.exists(common_path):
                exclude_set.update(load_exclusion_list(common_path))
            else:
                print(f"Warning: Common words file '{common_path}' not found.")

        words = process_text_file(args.input, exclude_set=exclude_set)
        if args.dev:
            print(f"Dev mode: limiting extraction to first 5 words.")
            words = words[:5]

        save_vocab_to_csv(words, args.output)
        return

    elif args.command == "mine-drama":
        exclude_set = set()
        if args.exclude:
            exclude_set.update(load_exclusion_list(args.exclude))
        if args.exclude_common:
            common_path = (Path.cwd() / "resources" / "vocab" / "1k.csv").as_posix()
            if os.path.exists(common_path):
                exclude_set.update(load_exclusion_list(common_path))
            else:
                print(f"Warning: Common words file '{common_path}' not found.")

        words = mine_subtitles(
            args.input, min_freq=args.min_freq, exclude_set=exclude_set
        )
        if args.dev:
            print(f"Dev mode: limiting extraction to first 5 words.")
            words = words[:5]

        save_vocab_to_csv(words, args.output)
        return

    elif args.command == "translate-vocab":
        words = load_vocab_from_csv(args.input)
        if args.llm:
            words = translate_with_gemini(words)
        else:
            words = translate_words_simple(words)
        save_vocab_to_csv(words, args.output)
        return

    elif args.command == "anki-deck":
        if args.input.endswith(".csv"):
            words = load_vocab_from_csv(args.input)
        else:
            words = process_text_file(args.input)
            if args.llm:
                words = translate_with_gemini(words)
            else:
                words = translate_words_simple(words)
        generate_anki_deck(words, args.output, args.name)
        return

    elif args.command == "align":
        # The align command does not require an ElevenLabs API key
        align_audio_text(args.audio, args.text, args.output, args.language, args.offset)
        return
    elif args.command == "align-all":
        align_all_audio_text(args.dir, args.language, args.offset)
        return

    # Initialize ElevenLabs client for voice commands
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print(
            "Error: ELEVENLABS_API_KEY environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        client = ElevenLabs(api_key=api_key)
    except Exception as e:
        print(f"Failed to initialize the ElevenLabs client: {e}")
        sys.exit(1)

    if args.command == "list-voices":
        list_voices(client, language=args.language, shared=args.shared)
    elif args.command == "sample":
        path = get_preview_path(args.voice)
        if path.exists():
            print(f"Using cached sample: {path}")
            play_audio(path)
        else:
            resolved_id = resolve_voice_id(client, args.voice)
            path = download_sample(client, resolved_id, args.voice)
            if path:
                play_audio(path)
    elif args.command == "tts":
        resolved_id = resolve_voice_id(client, args.voice)
        generate_tts(client, resolved_id, args.input, args.output)


if __name__ == "__main__":
    main()
