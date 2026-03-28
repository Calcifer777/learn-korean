# Task Completion Guidelines

1. **Verify Logic**: Run the specific CLI command affected by the change (use the `--dev` flag if it's a long-running vocabulary task) to ensure it works end-to-end without errors.
2. **Check Outputs**: Verify that the generated outputs (e.g., CSV files, `.apkg` files, `.lrc` files) are correctly formatted and contain the expected data.
3. **Format**: Ensure code aligns with the project's formatting rules (run `dprint fmt` if applicable).
4. **No Unnecessary Commits**: Do not commit changes to Git unless explicitly requested by the user.
