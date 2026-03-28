from google import genai
import os
import json
import re
from tqdm import tqdm


def translate_with_gemini(words: list[dict[str, str]]) -> list[dict[str, str]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. Skipping Gemini translation...")
        return words

    client = genai.Client(api_key=api_key)

    # Using the latest stable model
    model_id = "gemini-2.5-flash"

    print(
        f"Translating {len(words)} words with Gemini ({model_id}) context-aware logic..."
    )

    # Process in batches to be more efficient
    batch_size = 30
    translated_all = []

    for i in tqdm(
        range(0, len(words), batch_size), desc="Translating (Gemini)", unit="batch"
    ):
        batch = words[i : i + batch_size]

        prompt = """
        You are a Korean-English dictionary expert. I will provide you with a list of Korean words, their part of speech, and the sentence they were found in.

        For each entry:
        1.  Provide the English translation of the word that is most appropriate for that specific sentence context.
        2.  Provide the English translation of the entire example sentence.
        3.  Provide the Etymology: Identify the Sino-Korean (Hanja) roots and their literal English meanings (e.g., '기 (steam) + 차 (car)'). If the word is a pure native Korean word without Hanja roots, simply output 'Pure Korean'.

        Output the result ONLY as a JSON list of objects, each containing:
        - "Korean": the original word
        - "English": the word translation
        - "Sentence Translation": the sentence translation
        - "Etymology": the Hanja roots or 'Pure Korean'

        Input list:
        """

        input_data = []
        for w in batch:
            input_data.append(
                {
                    "Word": w["Korean"],
                    "POS": w["Part of Speech"],
                    "Sentence": w["Example Sentence"],
                }
            )

        prompt += json.dumps(input_data, ensure_ascii=False, indent=2)

        try:
            response = client.models.generate_content(model=model_id, contents=prompt)

            # Find JSON in the response
            text: str | None = response.text
            if text:
                match = re.search(r"\[.*\]", text, re.DOTALL)
                if match:
                    results = json.loads(match.group())
                    # Merge results back into original batch objects
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
            print(f"Error during Gemini translation batch {i // batch_size}: {e}")
            translated_all.extend(batch)  # Keep going anyway

    return translated_all


def extract_phrases_with_gemini(text: str, limit: int = 10) -> list[dict[str, str]]:
    """
    Uses Gemini to extract idiomatic phrases, collocations, and common 2-3 word blocks from a text.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. Skipping phrase extraction...")
        return []

    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.5-flash"

    print(f"Extracting top {limit} idiomatic phrases with Gemini...")

    prompt = f"""
    You are a Korean linguistics expert. I will provide you with a Korean text.
    Your task is to extract the top {limit} most useful 2- or 3-word 'blocks' from the text.
    These should be common collocations (e.g., '자리를 잡다'), idiomatic expressions, or frequent word pairings that are more meaningful when learned together than as individual words.

    For each block, output:
    1.  "Korean": The phrase exactly as it appears or its dictionary form (e.g., '자리를 잡다').
    2.  "English": A natural English translation.
    3.  "Etymology": A brief breakdown of the literal meaning of the components (e.g., '자리 (place/seat) + 잡다 (to catch/take)').
    4.  "Part of Speech": Always set to 'Phrase'.
    5.  "Example Sentence": The full sentence from the text where you found it.
    6.  "Sentence Translation": English translation of that sentence.

    Output the result ONLY as a JSON list of objects.

    Korean Text:
    {text}
    """

    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        res_text: str | None = response.text
        if res_text:
            match = re.search(r"\[.*\]", res_text, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f"Error during phrase extraction: {e}")

    return []
