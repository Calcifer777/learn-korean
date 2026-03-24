import ollama
import json
import re
from typing import List, Dict


def translate_with_ollama(
    words: List[Dict[str, str]], model: str = "llama3"
) -> List[Dict[str, str]]:
    print(
        f"Translating {len(words)} words with Ollama ({model}) context-aware logic..."
    )

    # Process in batches to be more efficient
    batch_size = 10  # Smaller batch for local LLM
    translated_all = []

    for i in range(0, len(words), batch_size):
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
            response = ollama.generate(model=model, prompt=prompt, think=False)
            # Find JSON in the response
            text = response["response"]
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                results = json.loads(match.group())
                # Merge results back into original batch objects
                for r in results:
                    for w in batch:
                        if w["Korean"] == r["Korean"]:
                            w["English"] = r.get("English", w.get("English", ""))
                            w["Sentence Translation"] = r.get("Sentence Translation", w.get("Sentence Translation", ""))
                            w["Etymology"] = r.get("Etymology", "")
            translated_all.extend(batch)
        except Exception as e:
            print(f"Error during Ollama translation batch {i//batch_size}: {e}")
            translated_all.extend(batch)  # Keep going anyway

    return translated_all
