import os
import tempfile
from learn_korean.parser import (
    extract_words_with_context,
    process_text_file,
    load_vocab_from_csv,
)


def test_extract_words_with_context_basic():
    # A simple Korean sentence with Nouns and Verbs
    text = "학교에 갑니다. 학생이 책을 읽어요."
    words = extract_words_with_context(text)

    assert isinstance(words, list)
    assert len(words) > 0

    # Check if '학교' (school) is extracted as Noun
    hakgyo = next((w for w in words if w["Korean"] == "학교"), None)
    assert hakgyo is not None
    assert hakgyo["Part of Speech"] == "Noun"
    assert hakgyo["Example Sentence"] == "학교에 갑니다."

    # Check if '가다' (to go) is extracted and lemmatized correctly (갑니다 -> 가다)
    gada = next((w for w in words if w["Korean"] == "가다"), None)
    assert gada is not None
    assert gada["Part of Speech"] == "Verb"

    # Ensure empty fields exist for later translation
    assert hakgyo["English"] == ""
    assert hakgyo["Sentence Translation"] == ""
    assert hakgyo["Etymology"] == ""


def test_extract_words_with_context_exclusion():
    text = "나는 매일 학교에 갑니다."
    # We want to exclude '나' (I) and '매일' (every day)
    exclude_set = {"나", "매일"}
    words = extract_words_with_context(text, exclude_set=exclude_set)

    lemmas = [w["Korean"] for w in words]
    assert "나" not in lemmas
    assert "매일" not in lemmas
    assert "학교" in lemmas
    assert "가다" in lemmas


def test_process_text_file_removes_timestamps():
    # Use a temporary file to simulate LRC input
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".md", encoding="utf-8"
    ) as tmp:
        tmp.write("[00:01.00] 학교에 갑니다.\n")
        tmp.write("[00:05.50] 집에 갑니다.\n")
        tmp_path = tmp.name

    try:
        words = process_text_file(tmp_path)
        # Should not contain any brackets or timestamps in the example sentences
        hakgyo = next((w for w in words if w["Korean"] == "학교"), None)
        assert hakgyo is not None
        assert hakgyo["Example Sentence"] == "학교에 갑니다."
    finally:
        os.remove(tmp_path)


def test_load_vocab_from_csv_handles_missing_columns():
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", encoding="utf-8-sig"
    ) as tmp:
        # Create a legacy CSV without 'Etymology' and 'Sentence Translation'
        tmp.write("Korean,Part of Speech,Example Sentence,English\n")
        tmp.write("학교,Noun,학교에 갑니다.,school\n")
        tmp_path = tmp.name

    try:
        vocab = load_vocab_from_csv(tmp_path)
        assert len(vocab) == 1
        word = vocab[0]

        assert word["Korean"] == "학교"
        assert word["English"] == "school"
        # Missing columns should be added dynamically
        assert "Sentence Translation" in word
        assert word["Sentence Translation"] == ""
        assert "Etymology" in word
        assert word["Etymology"] == ""
    finally:
        os.remove(tmp_path)
