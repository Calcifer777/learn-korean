from kiwipiepy import Kiwi
from deep_translator import GoogleTranslator
from typing import List, Dict, Tuple
import re
import pandas as pd

# Mapping Kiwi POS tags to friendly names
POS_MAP = {
    'NNG': 'Noun',
    'NNP': 'Noun',
    'NNB': 'Noun',
    'VV': 'Verb',
    'VA': 'Adjective',
    'MAG': 'Adverb',
    'MAJ': 'Adverb',
}

def extract_words_with_context(text: str) -> List[Dict[str, str]]:
    kiwi = Kiwi()
    # Split text into sentences using Kiwi
    sentences = kiwi.split_into_sents(text)
    
    unique_words: Dict[str, Dict[str, str]] = {} # lemma -> {pos, sentence}
    
    for sent in sentences:
        tokens = kiwi.tokenize(sent.text)
        for token in tokens:
            if token.tag in POS_MAP:
                lemma = token.form
                # For verbs and adjectives, add '다' to make it the dictionary form
                if token.tag in ['VV', 'VA'] and not lemma.endswith('다'):
                    lemma += '다'
                
                if lemma not in unique_words:
                    unique_words[lemma] = {
                        "Korean": lemma,
                        "Part of Speech": POS_MAP[token.tag],
                        "Example Sentence": sent.text.strip(),
                        "English": "",
                        "Sentence Translation": ""
                    }
    
    return list(unique_words.values())

def translate_words_simple(words: List[Dict[str, str]]) -> List[Dict[str, str]]:
    translator = GoogleTranslator(source='ko', target='en')
    print(f"Translating {len(words)} words (Simple Translation)...")
    
    for word in words:
        try:
            if not word.get("English"):
                word["English"] = translator.translate(word["Korean"])
            if not word.get("Sentence Translation") and word.get("Example Sentence"):
                word["Sentence Translation"] = translator.translate(word["Example Sentence"])
        except Exception as e:
            print(f"Warning: Could not translate '{word['Korean']}': {e}")
            
    return words

def process_text_file(file_path: str) -> List[Dict[str, str]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'\[\d{2}:\d{2}\.\d{2}\]', '', text)
    return extract_words_with_context(text)

def save_vocab_to_csv(words: List[Dict[str, str]], output_path: str):
    df = pd.DataFrame(words)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Vocab saved to {output_path}")

def load_vocab_from_csv(input_path: str) -> List[Dict[str, str]]:
    df = pd.read_csv(input_path)
    # Ensure all columns exist and fill NaNs
    for col in ["Korean", "Part of Speech", "Example Sentence", "English", "Sentence Translation"]:
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    return df.to_dict('records')
