from kiwipiepy import Kiwi
from deep_translator import GoogleTranslator

import re
import pandas as pd
from tqdm import tqdm

# Mapping Kiwi POS tags to friendly names
POS_MAP = {
    "NNG": "Noun",
    "NNP": "Noun",
    "NNB": "Noun",
    "VV": "Verb",
    "VA": "Adjective",
    "MAG": "Adverb",
    "MAJ": "Adverb",
}


def extract_words_with_context(
    text: str, exclude_set: set[str] | None = None, interactive: bool = False
) -> list[dict[str, str]]:
    kiwi = Kiwi()
    # Split text into sentences using Kiwi
    sentences = kiwi.split_into_sents(text)

    unique_words: dict[str, dict[str, str]] = {}  # lemma -> {pos, sentence}

    if exclude_set is None:
        exclude_set = set()

    for sent in tqdm(sentences, desc="Analyzing sentences", unit="sent"):
        tokens = kiwi.tokenize(sent.text)  # type: ignore
        for token in tokens:
            if token.tag in POS_MAP:  # type: ignore
                lemma: str = token.form  # type: ignore
                # For verbs and adjectives, add '다' to make it the dictionary form
                if token.tag in ["VV", "VA"] and not lemma.endswith("다"):  # type: ignore
                    lemma += "다"

                if lemma not in unique_words:
                    unique_words[lemma] = {
                        "Korean": lemma,
                        "Part of Speech": POS_MAP[token.tag],  # type: ignore
                        "Example Sentence": str(sent.text).strip(),  # type: ignore
                        "English": "",
                        "Sentence Translation": "",
                        "Etymology": "",
                    }

    results = list(unique_words.values())

    if not exclude_set:
        return results

    filtered = []
    for w in results:
        lemma = w["Korean"]
        if lemma in exclude_set:
            if interactive:
                ans = (
                    input(
                        f"Exclude common word '{lemma}'? (Context: {w['Example Sentence']}) [Y/n]: "
                    )
                    .strip()
                    .lower()
                )
                if ans == "n":
                    filtered.append(w)
        else:
            filtered.append(w)

    return filtered


def translate_words_simple(words: list[dict[str, str]]) -> list[dict[str, str]]:
    translator = GoogleTranslator(source="ko", target="en")
    print(f"Translating {len(words)} words (Simple Translation)...")

    for word in tqdm(words, desc="Translating", unit="word"):
        try:
            if not word.get("English"):
                word["English"] = translator.translate(word["Korean"])
            if not word.get("Sentence Translation") and word.get("Example Sentence"):
                word["Sentence Translation"] = translator.translate(
                    word["Example Sentence"]
                )
            if "Etymology" not in word:
                word["Etymology"] = ""
        except Exception as e:
            print(f"Warning: Could not translate '{word['Korean']}': {e}")

    return words


def process_text_file(
    file_path: str, exclude_set: set[str] | None = None, interactive: bool = False
) -> list[dict[str, str]]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"\[\d{2}:\d{2}\.\d{2}\]", "", text)
    return extract_words_with_context(text, exclude_set, interactive)


def save_vocab_to_csv(words: list[dict[str, str]], output_path: str):
    df = pd.DataFrame(words)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Vocab saved to {output_path}")


def load_vocab_from_csv(input_path: str) -> list[dict[str, str]]:
    df = pd.read_csv(input_path)
    # Ensure all columns exist and fill NaNs
    for col in [
        "Korean",
        "Part of Speech",
        "Example Sentence",
        "English",
        "Sentence Translation",
        "Etymology",
    ]:
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    # Cast to list[dict[str, str]] to satisfy type checker
    return list(df.to_dict("records"))  # type: ignore
