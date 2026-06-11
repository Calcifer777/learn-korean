import anthropic
import os
import json
import re
from tqdm import tqdm


def translate_with_claude(words: list[dict[str, str]]) -> list[dict[str, str]]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Warning: ANTHROPIC_API_KEY not found. Skipping Claude translation...")
        return words

    client = anthropic.Anthropic(api_key=api_key)
    model_id = "claude-sonnet-4-6"

    to_translate = [w for w in words if not w.get("English") or not w.get("Etymology")]
    already_translated = [w for w in words if w.get("English") and w.get("Etymology")]

    if not to_translate:
        return words

    print(
        f"Translating {len(to_translate)} words with Claude ({model_id}) context-aware logic..."
    )

    batch_size = 30
    translated_all = []

    for i in tqdm(
        range(0, len(to_translate), batch_size),
        desc="Translating (Claude)",
        unit="batch",
    ):
        batch = to_translate[i : i + batch_size]

        input_data = [
            {
                "Word": w.get("Korean", ""),
                "POS": w.get("Part of Speech", "unknown"),
                "Sentence": w.get("Example Sentence", ""),
            }
            for w in batch
        ]

        prompt = (
            "You are a Korean-English dictionary expert. I will provide you with a list of Korean words, "
            "their part of speech, and the sentence they were found in.\n\n"
            "For each entry:\n"
            "1. Provide the English translation most appropriate for that specific sentence context. "
            "For verbs, use the infinitive form.\n"
            "2. Provide the English translation of the entire example sentence.\n"
            "3. Provide the Etymology: identify Sino-Korean (Hanja) roots and their literal English meanings "
            "(e.g. 사용 -> 使 (사: use, employ) + 用 (용: use)). If the word is pure native Korean, output 'Pure Korean'.\n\n"
            "Output the result ONLY as a JSON list of objects, each containing:\n"
            '- "Korean": the original word\n'
            '- "English": the word translation\n'
            '- "Sentence Translation": the sentence translation\n'
            "- \"Etymology\": the Hanja roots or 'Pure Korean'\n\n"
            "Input list:\n" + json.dumps(input_data, ensure_ascii=False, indent=2)
        )

        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text if response.content else None  # type: ignore
            if text:
                match = re.search(r"\[.*\]", text, re.DOTALL)
                if match:
                    results = json.loads(match.group())
                    for r in results:
                        for w in batch:
                            if w["Korean"] == r["Korean"]:
                                w["English"] = r.get("English", w.get("English", ""))
                                w["Sentence Translation"] = r.get(
                                    "Sentence Translation",
                                    w.get("Sentence Translation", ""),
                                )
                                w["Etymology"] = r.get("Etymology", "")
            translated_all.extend(batch)
        except Exception as e:
            print(f"Error during Claude translation batch {i // batch_size}: {e}")
            translated_all.extend(batch)

    return already_translated + translated_all


def extract_phrases_with_claude(text: str, limit: int = 10) -> list[dict[str, str]]:
    """Uses Claude to extract idiomatic phrases, collocations, and common 2-3 word blocks."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Warning: ANTHROPIC_API_KEY not found. Skipping phrase extraction...")
        return []

    client = anthropic.Anthropic(api_key=api_key)
    model_id = "claude-sonnet-4-6"

    print(f"Extracting top {limit} idiomatic phrases with Claude...")

    prompt = (
        f"You are a Korean linguistics expert. I will provide you with a Korean text.\n"
        f"Your task is to extract the top {limit} most useful 2- or 3-word 'blocks' from the text.\n\n"
        "You must specifically target:\n"
        "- Idiomatic expressions & Collocations (e.g., '자리를 잡다', '영향을 받다')\n"
        "- Composed Verbs (e.g., '겪어보다' - to experience and see)\n"
        "- Complex Verb Phrases / Auxiliary Verbs (e.g., '차단해 버리다' - to completely block out)\n\n"
        "These blocks are more meaningful when learned together than as individual words.\n\n"
        "For each block, output:\n"
        '1. "Korean": The phrase exactly as it appears or its dictionary form.\n'
        '2. "English": A natural English translation.\n'
        '3. "Etymology": A brief breakdown of the literal meaning of the components.\n'
        "4. \"Part of Speech\": Always set to 'Phrase'.\n"
        '5. "Example Sentence": The full sentence from the text where you found it.\n'
        '6. "Sentence Translation": English translation of that sentence.\n\n'
        "Output the result ONLY as a JSON list of objects.\n\n"
        f"Korean Text:\n{text}"
    )

    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        res_text = response.content[0].text if response.content else None  # type: ignore
        if res_text:
            match = re.search(r"\[.*\]", res_text, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f"Error during phrase extraction: {e}")

    return []
