from google import genai
import os
import json
import re
from typing import List, Dict


def translate_with_gemini(words: List[Dict[str, str]]) -> List[Dict[str, str]]:
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

    for i in range(0, len(words), batch_size):
        batch = words[i : i + batch_size]

        prompt = """
        You are a Korean-English dictionary expert. I will provide you with a list of Korean words, their part of speech, and the sentence they were found in.
        
        For each entry:
        1.  Provide the English translation of the word that is most appropriate for that specific sentence context.
        2.  Provide the English translation of the entire example sentence.
        3.  Provide the Etymology: Identify the Sino-Korean (Hanja) roots and their literal English meanings (e.g., '기 (steam) + 차 (car)'). If the word is a pure native Korean word without Hanja roots, simply output 'Pure Korean'. Always write the root words in the Korean alphabet, not the Hanja ideogram or the romanized form
        
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
            text = response.text
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
            print(f"Error during Gemini translation batch {i//batch_size}: {e}")
            translated_all.extend(batch)  # Keep going anyway

    return translated_all
