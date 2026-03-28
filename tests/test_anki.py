import pytest
import os
import tempfile
import sqlite3
import zipfile
from learn_korean.anki_utils import generate_anki_deck

def test_generate_anki_deck_creates_valid_apkg():
    # Setup some test vocabulary containing etymology and translation
    words = [
        {
            "Korean": "도서관",
            "Part of Speech": "Noun",
            "English": "Library",
            "Example Sentence": "도서관에 갑니다.",
            "Sentence Translation": "I am going to the library.",
            "Etymology": "도 (picture) + 서 (book) + 관 (building)"
        },
        {
            "Korean": "책",
            "Part of Speech": "Noun",
            "English": "Book",
            "Example Sentence": "책을 읽어요.",
            "Sentence Translation": "I read a book.",
            "Etymology": "Pure Korean"
        },
        # Intentionally broken word without an English translation.
        # This should be gracefully ignored by the script.
        {
            "Korean": "학교",
            "Part of Speech": "Noun",
            "English": "",  # Missing English definition!
            "Example Sentence": "학교에 가요.",
        }
    ]

    with tempfile.NamedTemporaryFile(delete=False, suffix='.apkg') as tmp:
        apkg_path = tmp.name

    try:
        generate_anki_deck(words, apkg_path, "Test Korean Deck")

        # 1. Ensure the package file exists
        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0

        # 2. Extract the .apkg file (which is essentially a zip file)
        # to verify it contains the SQLite database representing the cards.
        with tempfile.TemporaryDirectory() as extract_dir:
            with zipfile.ZipFile(apkg_path, 'r') as z:
                z.extractall(extract_dir)
            
            # Anki 2.1 packages contain 'collection.anki2' or 'collection.anki21'
            db_path = os.path.join(extract_dir, 'collection.anki21')
            if not os.path.exists(db_path):
                db_path = os.path.join(extract_dir, 'collection.anki2')
                
            assert os.path.exists(db_path)

            # 3. Connect to the SQLite db to verify our notes were actually added
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Query the notes table
            cursor.execute("SELECT flds FROM notes")
            notes = cursor.fetchall()
            
            # Since the third word ("학교") didn't have an English translation,
            # it should have been skipped, resulting in exactly 2 notes.
            assert len(notes) == 2
            
            # The 'flds' column holds the content joined by '\x1f'.
            # Verify the primary key (Korean word) is in the notes.
            note_content = [n[0] for n in notes]
            assert any("도서관" in n for n in note_content)
            assert any("책" in n for n in note_content)
            assert not any("학교" in n for n in note_content)
            
            conn.close()

    finally:
        if os.path.exists(apkg_path):
            os.remove(apkg_path)
