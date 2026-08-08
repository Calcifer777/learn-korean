"""subtitle.py — LRC → ASS conversion and MKA muxing via ffmpeg."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

_TS_RE = re.compile(r"\[(\d+):(\d{2})\.(\d{2,3})\]")
_META_RE = re.compile(r"^\[[a-zA-Z#]+:")

# ASS colours: &HAABBGGRR  (alpha, blue, green, red — all hex pairs)
_ASS_HEADER = """\
[Script Info]
Title: Bilingual Korean/English
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Korean,Noto Sans CJK KR,58,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,2.5,1.5,2,40,40,25,1
Style: English,Arial,40,&H00FFE8D0,&H000000FF,&H00000000,&HA0000000,0,0,0,0,100,100,0,0,1,2,1,8,40,40,25,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
# Korean  → Alignment 2  (bottom centre) — the target language
# English → Alignment 8  (top centre)    — translation reference


def parse_lrc(path: Path) -> list[tuple[float, str]]:
    """Return sorted (start_seconds, text) pairs from an LRC file."""
    entries: list[tuple[float, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or _META_RE.match(line):
            continue
        stamps = _TS_RE.findall(line)
        if not stamps:
            continue
        text = _TS_RE.sub("", line).strip()
        if not text:
            continue
        for m, s, frac in stamps:
            frac_s = int(frac) / (100 if len(frac) == 2 else 1000)
            entries.append((int(m) * 60 + int(s) + frac_s, text))
    entries.sort(key=lambda e: e[0])
    return entries


def _with_ends(entries: list[tuple[float, str]]) -> list[tuple[float, float, str]]:
    """Derive end time for each cue (= next cue's start, or start + 5 s for last)."""
    out = []
    for i, (start, text) in enumerate(entries):
        end = entries[i + 1][0] if i + 1 < len(entries) else start + 5.0
        out.append((start, max(end, start + 0.5), text))
    return out


def _ts(sec: float) -> str:
    """Seconds → ASS timestamp  H:MM:SS.cc"""
    h = int(sec // 3600)
    m = int(sec % 3600 // 60)
    s = int(sec % 60)
    cs = round((sec % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _srt_ts(sec: float) -> str:
    """Seconds → SRT timestamp  HH:MM:SS,mmm"""
    h = int(sec // 3600)
    m = int(sec % 3600 // 60)
    s = int(sec % 60)
    ms = round((sec % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _to_srt(entries: list[tuple[float, float, str]]) -> str:
    """Render timed entries as an SRT string."""
    lines: list[str] = []
    for i, (start, end, text) in enumerate(entries, 1):
        lines += [str(i), f"{_srt_ts(start)} --> {_srt_ts(end)}", text, ""]
    return "\n".join(lines)


def build_ass(kr_path: Path, en_path: Path) -> str:
    """Parse two LRC files and return a bilingual ASS document as a string."""
    kr = _with_ends(parse_lrc(kr_path))
    en = _with_ends(parse_lrc(en_path))
    print(f"  Korean : {len(kr)} cues")
    print(f"  English: {len(en)} cues")

    lines: list[str] = [_ASS_HEADER.rstrip()]
    for start, end, text in kr:
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Korean,,0,0,0,,{text}")
    for start, end, text in en:
        lines.append(f"Dialogue: 1,{_ts(start)},{_ts(end)},English,,0,0,0,,{text}")
    lines.append("")
    return "\n".join(lines)


def mux_mka(
    mp3: Path,
    ass: Path,
    kr_lrc: Path,
    en_lrc: Path,
    output: Path,
    denoise: bool = False,
) -> None:
    """Mux mp3 + bilingual ASS + Korean SRT + English SRT into an MKA container.

    The LRC files are converted to SRT in Python (not by ffmpeg's LRC demuxer)
    so that end-times are well-defined and the container duration stays correct.
    When denoise=True the audio is run through afftdn and re-encoded as Opus.
    """
    kr_srt = _to_srt(_with_ends(parse_lrc(kr_lrc)))
    en_srt = _to_srt(_with_ends(parse_lrc(en_lrc)))

    with tempfile.NamedTemporaryFile(
        suffix=".srt", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(kr_srt)
        kr_tmp = Path(f.name)
    with tempfile.NamedTemporaryFile(
        suffix=".srt", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(en_srt)
        en_tmp = Path(f.name)

    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(mp3),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        duration = probe.stdout.strip()

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(mp3),  # 0: audio
            "-i",
            str(ass),  # 1: bilingual ASS
            "-i",
            str(kr_tmp),  # 2: Korean SRT
            "-i",
            str(en_tmp),  # 3: English SRT
            "-t",
            duration,
            *(
                ["-af", "afftdn=nr=12:nf=-40", "-c:a", "libopus", "-b:a", "128k"]
                if denoise
                else ["-c:a", "copy"]
            ),
            "-c:s:0",
            "ass",
            "-c:s:1",
            "subrip",
            "-c:s:2",
            "subrip",
            "-map",
            "0:a:0",
            "-map",
            "1:s:0",
            "-map",
            "2:s:0",
            "-map",
            "3:s:0",
            "-metadata:s:a:0",
            "language=kor",
            "-metadata:s:s:0",
            "language=und",
            "-metadata:s:s:0",
            "title=Korean / English",
            "-metadata:s:s:1",
            "language=kor",
            "-metadata:s:s:1",
            "title=Korean",
            "-metadata:s:s:2",
            "language=eng",
            "-metadata:s:s:2",
            "title=English",
            str(output),
        ]
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            print("Error: ffmpeg not found on PATH", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"ffmpeg failed (exit {e.returncode})", file=sys.stderr)
            sys.exit(e.returncode)
    finally:
        kr_tmp.unlink(missing_ok=True)
        en_tmp.unlink(missing_ok=True)
