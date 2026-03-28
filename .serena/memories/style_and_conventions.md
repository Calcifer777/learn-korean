# Code Style & Conventions

- **Language**: Python 3
- **Typing**: Type hints are heavily used and encouraged for function signatures.
- **Formatting**: `dprint` is used for formatting (presence of `dprint.json`).
- **Structure**: Source code is inside `src/learn_korean/`. The entry point is `__main__.py`, with logic modularized into `parser.py`, `miner.py`, `anki_utils.py`, and `translator_llm.py`.
- **Guidelines**: Adhere to PEP 8, maintain descriptive variable names, and provide clear CLI arguments using `argparse`.
