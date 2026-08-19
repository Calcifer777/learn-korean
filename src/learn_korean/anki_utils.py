import genanki
import hashlib

from tqdm import tqdm

# Define Card Styling (Catppuccin Frappe Theme)
STYLE = """
.card {
 font-family: arial;
 font-size: 20px;
 text-align: center;
 background-color: transparent;
 color: #C6D0F5; /* Frappé Text */
}

.korean {
 font-size: 40px;
 font-weight: bold;
 color: #F4B8E4; /* Frappé Pink */
 margin-bottom: 20px;
}

.english {
 color: #C6D0F5; /* Frappé Text */
 font-size: 24px;
 font-weight: bold;
 margin-bottom: 10px;
}

.pos {
 font-size: 14px;
 color: #A6D189; /* Frappé Green */
 padding: 5px;
 border: 1px solid #A6D189;
 border-radius: 5px;
 display: inline-block;
 margin-top: 10px;
}

.sentence-container {
    margin-top: 25px;
    padding: 10px;
    background-color: rgba(65, 69, 89, 0.3); /* Frappé Surface0 with opacity */
    border-radius: 10px;
    font-size: 16px;
    text-align: left;
    display: inline-block;
    max-width: 90%;
}

.sentence-kr {
    color: #8CAAEE; /* Frappé Blue */
    font-style: italic;
    margin-bottom: 5px;
}

.sentence-en {
    color: #949CBB; /* Frappé Subtext0 */
    font-size: 14px;
}

.rank {
 font-size: 12px;
 color: #838BA7; /* Frappé Overlay1 */
 margin-top: 20px;
}

hr {
    border: 0;
    height: 1px;
    background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(198, 208, 245, 0.75), rgba(0, 0, 0, 0));
    margin: 20px 0;
}
"""


def get_stable_id(name: str) -> int:
    """Generate a stable 10-digit integer ID from a string."""
    return int(hashlib.sha256(name.encode("utf-8")).hexdigest(), 16) % (10**10)


VOCAB_FIELDS = [
    {"name": "Korean"},
    {"name": "Rank"},
    {"name": "English"},
    {"name": "Part of Speech"},
    {"name": "Example Sentence"},
    {"name": "Sentence Translation"},
    {"name": "Etymology"},
]

VOCAB_CSS = (
    STYLE
    + """
.etymology {
    font-size: 14px;
    font-style: italic;
    color: #E5C890; /* Frappé Yellow */
    margin-top: 10px;
}
"""
)

KOREAN_TO_ENGLISH_TEMPLATE = {
    "name": "Korean -> English",
    "qfmt": """
        <div class="korean">{{Korean}}</div>
    """,
    "afmt": """
        {{FrontSide}}
        <hr id="answer">
        <div class="english">{{English}}</div>
        <div class="pos">{{Part of Speech}}</div>
        {{#Etymology}}
        <div class="etymology">{{Etymology}}</div>
        {{/Etymology}}

        <div class="sentence-container">
            <div class="sentence-kr">{{Example Sentence}}</div>
            <div class="sentence-en">{{Sentence Translation}}</div>
        </div>

        <div class="rank">Rank: #{{Rank}}</div>
    """,
}

ENGLISH_TO_KOREAN_TEMPLATE = {
    "name": "English -> Korean",
    "qfmt": """
        <div class="english">{{English}}</div>
        <div class="pos">{{Part of Speech}}</div>
    """,
    "afmt": """
        {{FrontSide}}
        <hr id="answer">
        <div class="korean">{{Korean}}</div>
        {{#Etymology}}
        <div class="etymology">{{Etymology}}</div>
        {{/Etymology}}

        <div class="sentence-container">
            <div class="sentence-kr">{{Example Sentence}}</div>
            <div class="sentence-en">{{Sentence Translation}}</div>
        </div>

        <div class="rank">Rank: #{{Rank}}</div>
    """,
}


def create_recall_model():
    """English -> Korean only. Default model for generate_anki_deck."""
    model_id = get_stable_id("Context-Aware Korean Vocab v4 (Recall)")
    return genanki.Model(
        model_id,
        "Context-Aware Korean Vocab (Recall)",
        fields=VOCAB_FIELDS,
        templates=[ENGLISH_TO_KOREAN_TEMPLATE],
        css=VOCAB_CSS,
    )


def create_bidirectional_model():
    """Korean -> English and English -> Korean. Kept as an alternate style;
    not used by default since English -> Korean recall alone is preferred.
    """
    # Use a stable ID so re-importing doesn't create duplicate models in Anki
    model_id = get_stable_id("Context-Aware Korean Vocab v3")
    return genanki.Model(
        model_id,
        "Context-Aware Korean Vocab",
        fields=VOCAB_FIELDS,
        templates=[KOREAN_TO_ENGLISH_TEMPLATE, ENGLISH_TO_KOREAN_TEMPLATE],
        css=VOCAB_CSS,
    )


def truncate_sentence(sentence: str, target_word: str, max_eojeols: int = 12) -> str:
    """Truncate a Korean sentence to at most `max_eojeols` space-separated
    chunks, keeping a window centered on the eojeol containing `target_word`.
    Adds an ellipsis on whichever side gets cut.
    """
    tokens = sentence.split()
    if len(tokens) <= max_eojeols:
        return sentence

    target_idx = next(
        (i for i, t in enumerate(tokens) if target_word in t), len(tokens) // 2
    )
    half = max_eojeols // 2
    start = max(0, target_idx - half)
    end = min(len(tokens), start + max_eojeols)
    start = max(0, end - max_eojeols)  # re-clamp if end hit the right edge

    window = tokens[start:end]
    if start > 0:
        window[0] = "... " + window[0]
    if end < len(tokens):
        window[-1] = window[-1] + " ..."
    return " ".join(window)


POS_ABBREV = {"Noun": "n", "Verb": "v", "Adjective": "adj", "Adverb": "adv"}


def abbrev_pos(pos: str) -> str:
    return POS_ABBREV.get(pos, pos.lower())


SENTENCE_FIELDS = [
    {"name": "Sentence"},
    {"name": "Glossary"},
    {"name": "Sentence Translation"},
    {"name": "Rank"},
]

SENTENCE_TO_MEANING_TEMPLATE = {
    "name": "Sentence -> Meaning",
    "qfmt": """
        <div class="sentence-container">
            <div class="sentence-kr">{{Sentence}}</div>
        </div>
    """,
    "afmt": """
        {{FrontSide}}
        <hr id="answer">
        <div class="sentence-container">
            <div class="sentence-en">{{Sentence Translation}}</div>
        </div>
        <div class="glossary">{{Glossary}}</div>
        <div class="rank">Rank: #{{Rank}}</div>
    """,
}

TRANSLATION_TO_SENTENCE_TEMPLATE = {
    "name": "Translation -> Sentence",
    "qfmt": """
        <div class="sentence-container">
            <div class="sentence-en">{{Sentence Translation}}</div>
        </div>
    """,
    "afmt": """
        {{FrontSide}}
        <hr id="answer">
        <div class="sentence-container">
            <div class="sentence-kr">{{Sentence}}</div>
        </div>
        <div class="glossary">{{Glossary}}</div>
        <div class="rank">Rank: #{{Rank}}</div>
    """,
}

SENTENCE_CSS = (
    STYLE
    + """
.sentence-kr {
    color: #8CAAEE; /* Frappé Blue */
    font-size: 22px;
}

.sentence-container {
    background-color: rgba(65, 69, 89, 0.3);
}

.sentence-en {
    color: #deddda;
    font-size: 19px;
}

.glossary {
    text-align: left;
    display: table;
    margin: 30px auto 0;
}

.glossary-entry {
    margin-bottom: 12px;
}

.glossary-entry b {
    color: #C6D0F5; /* Frappé Text */
    font-size: 14px;
}

.glossary-entry .pos-tag {
    font-size: 12px;
    color: #A6D189; /* Frappé Green */
}

.glossary-entry .eng {
    color: #C6D0F5; /* Frappé Text */
    font-size: 15px;
}

.etymology {
    font-size: 11px;
    font-style: italic;
    color: #E5C890; /* Frappé Yellow */
    margin-top: 2px;
}
"""
)


def create_sentence_model():
    """Translation -> Sentence recall only. Default model for generate_sentence_deck."""
    model_id = get_stable_id("Sentence-Context Korean v7 (Recall)")
    return genanki.Model(
        model_id,
        "Sentence-Context Korean (Recall)",
        fields=SENTENCE_FIELDS,
        templates=[TRANSLATION_TO_SENTENCE_TEMPLATE],
        css=SENTENCE_CSS,
    )


def create_sentence_recognition_model():
    """Sentence -> Meaning. Kept as an alternate style; not used by default
    since Translation -> Sentence recall alone is preferred.
    """
    model_id = get_stable_id("Sentence-Context Korean v6")
    return genanki.Model(
        model_id,
        "Sentence-Context Korean",
        fields=SENTENCE_FIELDS,
        templates=[SENTENCE_TO_MEANING_TEMPLATE],
        css=SENTENCE_CSS,
    )


def generate_sentence_deck(
    words: list[dict[str, str]], output_file: str, deck_name: str
):
    """
    words: same shape as generate_anki_deck's input. Groups entries that share
    the same Example Sentence into one card: front shows the sentence with
    every target word bolded, back lists each word's meaning/etymology.
    """
    deck_id = get_stable_id(deck_name)
    my_model = create_sentence_model()
    my_deck = genanki.Deck(deck_id, deck_name)

    groups: dict[str, list[dict[str, str]]] = {}
    for word in words:
        sentence = word.get("Example Sentence", "")
        if not word.get("Korean") or not word.get("English") or not sentence:
            continue
        groups.setdefault(sentence, []).append(word)

    for i, (sentence, group) in enumerate(
        tqdm(groups.items(), desc=f"Creating deck '{deck_name}'", unit="note"), 1
    ):
        display_sentence = (
            truncate_sentence(sentence, group[0]["Korean"])
            if len(group) == 1
            else sentence
        )
        for w in group:
            display_sentence = display_sentence.replace(
                w["Korean"], f"<b>{w['Korean']}</b>", 1
            )

        glossary_html = "".join(
            f'<div class="glossary-entry"><b>{w["Korean"]}</b> '
            f'<span class="pos-tag">({abbrev_pos(w.get("Part of Speech", ""))})</span> '
            f'<span class="eng">&mdash; {w.get("English", "")}</span>'
            + (
                f'<div class="etymology">{w["Etymology"]}</div>'
                if w.get("Etymology")
                else ""
            )
            + "</div>"
            for w in group
        )

        note_guid = genanki.guid_for(deck_name, sentence)
        note = genanki.Note(
            model=my_model,
            fields=[
                display_sentence,
                glossary_html,
                group[0].get("Sentence Translation", ""),
                str(i),
            ],
            guid=note_guid,
        )
        my_deck.add_note(note)

    genanki.Package(my_deck).write_to_file(output_file)
    print(
        f"Successfully created sentence-context deck: {output_file} with {len(my_deck.notes)} notes."
    )


def generate_anki_deck(words: list[dict[str, str]], output_file: str, deck_name: str):
    """
    words: List of dicts with keys: 'Korean', 'English', 'Part of Speech', 'Example Sentence', 'Sentence Translation', 'Etymology'
    """
    # Use a stable deck ID based on the deck name
    deck_id = get_stable_id(deck_name)
    my_model = create_recall_model()
    my_deck = genanki.Deck(deck_id, deck_name)

    for i, word in enumerate(
        tqdm(words, desc=f"Creating deck '{deck_name}'", unit="note"), 1
    ):
        # Skip notes that have no Korean or English to avoid broken cards
        if not word.get("Korean") or not word.get("English"):
            continue

        # Use a stable GUID for each note to prevent duplicates on re-import,
        # but scope it to the specific deck so the same word can appear in different decks.
        note_guid = genanki.guid_for(
            deck_name, word["Korean"], word.get("Part of Speech", "")
        )

        note = genanki.Note(
            model=my_model,
            fields=[
                word.get("Korean", ""),
                str(i),
                word.get("English", ""),
                word.get("Part of Speech", "unknown"),
                word.get("Example Sentence", ""),
                word.get("Sentence Translation", ""),
                word.get("Etymology", ""),
            ],
            guid=note_guid,
        )
        my_deck.add_note(note)

    genanki.Package(my_deck).write_to_file(output_file)
    print(
        f"Successfully created context-aware deck: {output_file} with {len(my_deck.notes)} notes."
    )
