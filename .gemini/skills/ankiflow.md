---
name: vocabulary management
description:
  Expertise in vocabulary resource management. List vocabulary categories and download the glossary
---

# Ankiflow

You can use the **ankiflow** tool to list and download the vocabulary categories.

Always invoke ankiflow with `uv` (e.g. `uv run ankiflow ...`)

Available commands

1. **Find the category index:**: `uvx ankiflow list-categories --type semantic`
2. **Download the words:**: `uvx ankiflow download --semantic 8 --output ./resources/vocabulary/` (8 would be the category id)

