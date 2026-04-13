# gitgraffiti - Agent Instructions

You are helping a user paint text on their GitHub contribution graph using gitgraffiti.

## Overview

`gitgraffiti.py` is a Python CLI that creates backdated empty git commits to spell out words on a GitHub contribution graph. It renders text using a built-in 5x7 pixel font, maps pixels to dates, and pushes to a repo.

## Step-by-step workflow

1. **Ask the user** what text they want to display and which year to target. A year with no existing commits works best.

2. **Preview first** — always do a dry run before committing:
   ```bash
   python3 gitgraffiti.py "TEXT" --year YYYY --dry-run
   ```
   Show the user the preview output and get confirmation before proceeding.

3. **Create a dedicated repo** for the output. Never push graffiti commits to a repo with real code. Use `gh` or ask the user to create one:
   ```bash
   gh repo create graffiti-art --private
   ```

4. **Run the tool** with the repo URL. The script will prompt for confirmation — pipe `y` via stdin:
   ```bash
   python3 gitgraffiti.py "TEXT" --year YYYY --repo https://github.com/USER/REPO.git <<< "y"
   ```

5. **Verify** by telling the user to check their GitHub profile. It may take a few minutes to update.

## Constraints

- **Max width**: 52 columns. Most 5-6 letter words fit; 8 letters is the practical max.
- **Supported characters**: A-Z, 0-9, space, `! - . _ #`
- **Best results**: Target a year where the user had no GitHub activity.
- **Timeout**: The commit process can take a few minutes for long text. Use a generous timeout (300s).

## Options reference

| Flag | Description | Default |
|------|-------------|---------|
| `--repo URL` | GitHub repo to push to | _(none)_ |
| `--year YYYY` | Target year | Current year |
| `--intensity N` | Commits per active cell | 15 |
| `--spacing N` | Blank columns between letters | 1 |
| `--align` | `left`, `center`, or `right` | `center` |
| `--dry-run` | Preview only, no commits | |

## Common issues

- **Text too long**: Reduce `--spacing` to 0, or use shorter text.
- **Text not visible on profile**: The repo must be owned by the user (not an org). The repo can be private — GitHub still counts private contributions if that setting is enabled in the user's profile.
- **Existing activity that year**: Increase `--intensity` (e.g., 30-50) so the text cells are darker than the background noise.
