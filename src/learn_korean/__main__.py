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
            print(f"Resolved name '{voice_input}' to shared library voice ID '{shared.voices[0].voice_id}'")
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
                    print(f"- {voice.name} (ID: {voice.voice_id}) [Category: {category}]{label_str}")
            
            if not found:
                print("No matching voices found in your account.")
    except Exception as e:
        print(f"Error listing voices: {e}", file=sys.stderr)
        sys.exit(1)


def download_sample(client: ElevenLabs, resolved_id: str, voice_input: str) -> Path | None:
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
            print(f"Error: Could not locate a preview URL for voice ID '{resolved_id}'.")
            return None

        actual_name_path = get_preview_path(voice_name)

        print(f"Downloading sample for '{voice_name}' from: {preview_url}")
        req = urllib.request.Request(preview_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = response.read()
            
            with open(target_path, 'wb') as out_file:
                out_file.write(data)
                
            if target_path != actual_name_path and not actual_name_path.exists():
                with open(actual_name_path, 'wb') as out_file:
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


def _process_alignment(model, audio_path: str, text_path: str, output_path: str, language: str, offset_ms: int) -> None:
    """Core logic to read, clean, align, and save subtitles."""
    # Read and clean the text file
    with open(text_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
        
    # Strip existing LRC timestamps like [00:00.00] if they exist
    clean_text = re.sub(r'\[\d{2}:\d{2}\.\d{2}\]', '', raw_text)
    # Collapse multiple newlines/spaces
    clean_text = re.sub(r'\n+', ' ', clean_text).strip()
    
    if not clean_text:
        raise ValueError(f"The text file '{text_path}' appears to be empty after cleaning.")

    print(f"Aligning '{os.path.basename(audio_path)}' to the text (this might take a moment)...")
    result = model.align(audio_path, clean_text, language=language)

    offset_seconds = offset_ms / 1000.0
    print(f"Writing synchronized subtitles to '{os.path.basename(output_path)}' with a {offset_ms}ms offset...")
    with open(output_path, "w", encoding="utf-8") as f:
        for segment in result.segments:
            # Apply offset and ensure time is not negative
            synced_start = max(0, segment.start + offset_seconds)
            timestamp = format_timestamp(synced_start)
            f.write(f"{timestamp} {segment.text.strip()}\n")


def align_audio_text(audio_file: str, text_file: str, output_file: str, language: str = 'ko', offset_ms: int = -200) -> None:
    """Aligns audio with text using stable-ts and faster-whisper, generating an LRC file."""
    try:
        print(f"Loading faster-whisper 'base' model via stable-ts...")
        # Use compute_type='int8' to ensure it runs comfortably on most machines
        model = stable_whisper.load_faster_whisper('base', compute_type='int8')
        
        _process_alignment(model, audio_file, text_file, output_file, language, offset_ms)

        print("Alignment complete! ✨")
        
    except Exception as e:
        print(f"Error during alignment: {e}", file=sys.stderr)
        sys.exit(1)


def align_all_audio_text(directory: str, language: str = 'ko', offset_ms: int = -200) -> None:
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
        model = stable_whisper.load_faster_whisper('base', compute_type='int8')
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        sys.exit(1)

    for audio_path in mp3_files:
        lrc_path = audio_path.with_suffix('.lrc')
        if not lrc_path.exists():
            print(f"Skipping '{audio_path.name}': No matching .lrc file found.")
            continue

        print(f"\nProcessing '{audio_path.name}'...")
        try:
            _process_alignment(model, str(audio_path), str(lrc_path), str(lrc_path), language, offset_ms)
            print(f"Successfully aligned '{lrc_path.name}'.")
        except Exception as e:
            print(f"Error processing '{audio_path.name}': {e}", file=sys.stderr)

    print("\nBulk alignment complete! ✨")


def main() -> None:
    parser = argparse.ArgumentParser(description="ElevenLabs TTS & Subtitle Alignment Tool")
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # Command: List voices
    list_parser = subparsers.add_parser(
        "list-voices", help="List all available ElevenLabs voices"
    )
    list_parser.add_argument(
        "--language", help="Filter voices by language/accent label (e.g., 'ko' for Korean)"
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
    align_parser = subparsers.add_parser("align", help="Force-align text to an audio file using stable-ts")
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
        "--offset", type=int, default=-200, help="Offset in milliseconds to shift timestamps (default: -200)"
    )

    # Command: Align All
    align_all_parser = subparsers.add_parser("align-all", help="Force-align all MP3/LRC pairs in a directory using stable-ts")
    align_all_parser.add_argument(
        "--dir", required=True, help="Path to the directory containing MP3 and LRC files"
    )
    align_all_parser.add_argument(
        "--language", default="ko", help="Language code of the audio (default: ko)"
    )
    align_all_parser.add_argument(
        "--offset", type=int, default=-200, help="Offset in milliseconds to shift timestamps (default: -200)"
    )

    args = parser.parse_args()

    if args.command == "align":
        # The align command does not require an ElevenLabs API key
        align_audio_text(args.audio, args.text, args.output, args.language, args.offset)
        return
    elif args.command == "align-all":
        align_all_audio_text(args.dir, args.language, args.offset)
        return

    # Initialize ElevenLabs client for voice commands
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY environment variable is not set.", file=sys.stderr)
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
