import pandas as pd
import genanki
import argparse
import random
import sys


def create_deck(input_csv, output_file, deck_name="Korean Top 1000"):
    # 1. Generate unique IDs
    model_id = random.randrange(1 << 30, 1 << 31)
    deck_id = random.randrange(1 << 30, 1 << 31)

    # 2. Define Card Styling (Catppuccin Frappe Theme)
    style = """
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

    # 3. Define the Anki Model with TWO Templates
    my_model = genanki.Model(
        model_id,
        "Bidirectional Korean Vocab v2",
        fields=[
            {"name": "Rank"},
            {"name": "Korean"},
            {"name": "English"},
            {"name": "Part of Speech"},
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
                    <div class="rank">Rank: #{{Rank}}</div>
                """,
            },
        ],
        css=style,
    )

    # 4. Create the Deck
    my_deck = genanki.Deck(deck_id, deck_name)

    # 5. Read CSV and Add Notes
    try:
        df = pd.read_csv(input_csv)
        df["Rank"] = range(1, len(df) + 1)
        df.columns = df.columns.str.strip()  # Clean column names
        print(f"Reading {len(df)} rows from '{input_csv}'...")
    except FileNotFoundError:
        print(f"Error: The file '{input_csv}' was not found.")
        sys.exit(1)

    # Validate Columns (Romanization is no longer required)
    required_cols = ["Rank", "Korean", "English", "Part of Speech"]
    if not all(col in df.columns for col in required_cols):
        print(f"Error: CSV is missing required columns. Need: {required_cols}")
        sys.exit(1)

    for index, row in df.iterrows():
        note = genanki.Note(
            model=my_model,
            fields=[
                str(row["Rank"]),
                str(row["Korean"]),
                str(row["English"]),
                str(row["Part of Speech"]),
            ],
        )
        my_deck.add_note(note)

    # 6. Save the Deck
    genanki.Package(my_deck).write_to_file(output_file)
    print(f"Successfully created bidirectional deck: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert Korean CSV to Bidirectional Anki Deck (No Romanization)."
    )
    parser.add_argument("input_csv", help="Path to the input CSV file.")
    parser.add_argument("output_file", help="Path for the output .apkg file.")
    parser.add_argument(
        "--name",
        "-n",
        default="Korean Top 1000 (Bidirectional)",
        help="Name of the deck inside Anki",
    )

    args = parser.parse_args()

    create_deck(args.input_csv, args.output_file, args.name)
