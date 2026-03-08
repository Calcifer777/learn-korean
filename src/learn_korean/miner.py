import re
import pandas as pd
from typing import List, Dict, Set
from kiwipiepy import Kiwi
from collections import Counter
from .parser import POS_MAP

def parse_lrc(file_path: str) -> List[str]:
    """Extracts text lines from an LRC file, removing timestamps."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    clean_lines = []
    for line in lines:
        # Match [MM:SS.xx] pattern
        text = re.sub(r'\[\d{2}:\d{2}\.\d{2}\]', '', line).strip()
        # Remove technical descriptions in brackets [like this]
        text = re.sub(r'\[[^\]]+\]', '', text).strip()
        # Remove speaker names in parentheses (like this)
        text = re.sub(r'\([^)]+\)', '', text).strip()
        
        if text:
            clean_lines.append(text)
    return clean_lines

def parse_srt(file_path: str) -> List[str]:
    """Extracts text lines from an SRT file, removing timestamps and formatting."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    clean_lines = []
    
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            text_lines = lines[2:]
            text = " ".join(text_lines)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text).strip()
            # Remove technical descriptions in brackets [like this]
            text = re.sub(r'\[[^\]]+\]', '', text).strip()
            # Remove speaker names in parentheses (like this)
            text = re.sub(r'\([^)]+\)', '', text).strip()
            
            if text:
                clean_lines.append(text)
                
    return clean_lines

def mine_subtitles(file_path: str, min_freq: int = 2, exclude_csv: str = None) -> List[Dict[str, str]]:
    kiwi = Kiwi()
    
    if file_path.lower().endswith('.lrc'):
        lines = parse_lrc(file_path)
    elif file_path.lower().endswith('.srt'):
        lines = parse_srt(file_path)
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
            
    all_text = " ".join(lines)
    
    known_words: Set[str] = set()
    if exclude_csv:
        try:
            df_known = pd.read_csv(exclude_csv)
            if 'Korean' in df_known.columns:
                known_words = set(df_known['Korean'].astype(str).tolist())
        except Exception as e:
            print(f"Warning: Could not load exclusion list {exclude_csv}: {e}")

    tokens = kiwi.tokenize(all_text)
    word_counts = Counter()
    lemma_to_pos = {}
    
    for token in tokens:
        if token.tag in POS_MAP:
            lemma = token.form
            if token.tag in ['VV', 'VA'] and not lemma.endswith('다'):
                lemma += '다'
            
            # Skip very short words (usually particles or common filler)
            if len(lemma) < 2 and lemma not in ['가', '오', '내']:
                continue
                
            if lemma not in known_words:
                word_counts[lemma] += 1
                lemma_to_pos[lemma] = POS_MAP[token.tag]

    target_words = [word for word, count in word_counts.items() if count >= min_freq]
    target_words.sort(key=lambda x: word_counts[x], reverse=True)

    results = []
    for word in target_words:
        example_sentence = ""
        for line in lines:
            search_term = word[:-1] if word.endswith('다') and len(word) > 1 else word
            if search_term in line:
                example_sentence = line
                break
        
        results.append({
            "Korean": word,
            "Part of Speech": lemma_to_pos[word],
            "Frequency": word_counts[word],
            "Example Sentence": example_sentence,
            "English": "",
            "Sentence Translation": ""
        })

    return results
