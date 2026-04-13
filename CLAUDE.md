# gitgraffiti

Paint text on a user's GitHub contribution graph by creating backdated empty commits.

## Quick start

```bash
# Always preview first
python3 gitgraffiti.py "TEXT" --year YYYY --dry-run

# Create a separate repo for the commits (never pollute real repos)
gh repo create graffiti-art --private

# Run it (pipe y to confirm)
python3 gitgraffiti.py "TEXT" --year YYYY --repo https://github.com/USER/REPO.git <<< "y"
```

## Important

- Always `--dry-run` first and show the user the preview before committing.
- Always create a **separate dedicated repo** for graffiti output. Do not push to repos containing real code.
- Target a year with **no existing commits** for cleanest results. Ask the user which year works.
- The commit step can take a few minutes — use a 300s timeout.
- Supported characters: A-Z, 0-9, space, and `! - . _ #`. Max ~8 characters fit in the 52-column graph.
- If the user has existing activity that year, increase `--intensity` (e.g., 30+) so the text stands out.
