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


def create_bidirectional_model():
    # Use a stable ID so re-importing doesn't create duplicate models in Anki
    model_id = get_stable_id("Context-Aware Korean Vocab v3")
    return genanki.Model(
        model_id,
        "Context-Aware Korean Vocab",
        fields=[
            {"name": "Korean"},
            {"name": "Rank"},
            {"name": "English"},
            {"name": "Part of Speech"},
            {"name": "Example Sentence"},
            {"name": "Sentence Translation"},
            {"name": "Etymology"},
        ],
        templates=[
            # Template 1: Korean -> English (Recognition)
            {
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
            },
            # Template 2: English -> Korean (Recall)
            {
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
            },
        ],
        css=STYLE
        + """
.etymology {
    font-size: 14px;
    font-style: italic;
    color: #E5C890; /* Frappé Yellow */
    margin-top: 10px;
}
""",
    )


def generate_anki_deck(words: list[dict[str, str]], output_file: str, deck_name: str):
    """
    words: List of dicts with keys: 'Korean', 'English', 'Part of Speech', 'Example Sentence', 'Sentence Translation', 'Etymology'
    """
    # Use a stable deck ID based on the deck name
    deck_id = get_stable_id(deck_name)
    my_model = create_bidirectional_model()
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
