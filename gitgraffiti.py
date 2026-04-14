#!/usr/bin/env python3
"""gitgraffiti - paint words on your GitHub contribution graph by backdating commits."""

import argparse
import datetime
import os
import subprocess
import sys
import tempfile
import time

# 5×7 pixel font. Each char = list of 7 rows, each row = 5-bit int (MSB = left).
FONT = {
    'A': [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    'B': [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    'C': [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    'D': [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
    'E': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    'F': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    'G': [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0E],
    'H': [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    'I': [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    'J': [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    'K': [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    'L': [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    'M': [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    'N': [0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11],
    'O': [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    'P': [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    'Q': [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    'R': [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    'S': [0x0E, 0x11, 0x10, 0x0E, 0x01, 0x11, 0x0E],
    'T': [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    'U': [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    'V': [0x11, 0x11, 0x11, 0x11, 0x0A, 0x0A, 0x04],
    'W': [0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A],
    'X': [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    'Y': [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    'Z': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    '0': [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    '1': [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    '2': [0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F],
    '3': [0x0E, 0x11, 0x01, 0x06, 0x01, 0x11, 0x0E],
    '4': [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    '5': [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    '6': [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    '7': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    '8': [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    '9': [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    '!': [0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04],
    '-': [0x00, 0x00, 0x00, 0x0E, 0x00, 0x00, 0x00],
    '.': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04],
    '_': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F],
    '#': [0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A],
}

DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']


def text_to_grid(text, spacing=1):
    """Convert text to a list of columns, each column is a list of 7 bools."""
    columns = []
    for i, ch in enumerate(text):
        if ch not in FONT:
            print(f"Warning: no glyph for '{ch}', using space", file=sys.stderr)
            ch = ' '
        if i > 0:
            for _ in range(spacing):
                columns.append([False] * 7)
        glyph = FONT[ch]
        for col in range(5):
            bit = 4 - col
            columns.append([bool(glyph[row] >> bit & 1) for row in range(7)])
    return columns


def preview(columns, offset):
    """Print a visual preview of the contribution graph."""
    print()
    for row in range(7):
        line = f"  {DAYS[row]} "
        for col in range(52):
            if offset <= col < offset + len(columns):
                if columns[col - offset][row]:
                    line += "█ "
                else:
                    line += "· "
            else:
                line += "· "
        print(line)
    print()


def get_start_sunday(year):
    """Get the first Sunday of the contribution graph for a given year."""
    jan1 = datetime.date(year, 1, 1)
    # GitHub graph starts on the Sunday of the week containing Jan 1
    # Actually, the graph shows the last 52 weeks. For a specific year,
    # we start from the first Sunday on or before Jan 1.
    dow = jan1.weekday()  # Monday=0, Sunday=6
    # Convert to Sun=0 convention
    dow_sun = (dow + 1) % 7
    if dow_sun == 0:
        return jan1
    else:
        return jan1 + datetime.timedelta(days=(7 - dow_sun))


def main():
    parser = argparse.ArgumentParser(
        description="gitgraffiti - paint words on your GitHub contribution graph"
    )
    parser.add_argument("text", help="Text to display")
    parser.add_argument("--repo", help="GitHub repo URL to push to")
    parser.add_argument("--year", type=int, default=datetime.date.today().year)
    parser.add_argument("--intensity", type=int, default=1,
                        help="Commits per active cell (default: 1, increase if year has existing activity)")
    parser.add_argument("--spacing", type=int, default=1,
                        help="Blank columns between letters (default: 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without making commits")
    parser.add_argument("--align", choices=["left", "center", "right"],
                        default="center", help="Horizontal alignment (default: center)")
    args = parser.parse_args()

    text = args.text.upper()
    columns = text_to_grid(text, args.spacing)

    if len(columns) > 52:
        print(f"Error: text needs {len(columns)} columns but the graph only has 52.", file=sys.stderr)
        print("Try shorter text or --spacing 0", file=sys.stderr)
        sys.exit(1)

    if args.align == "center":
        offset = (52 - len(columns)) // 2
    elif args.align == "left":
        offset = 0
    else:
        offset = 52 - len(columns)

    preview(columns, offset)

    active = sum(1 for col in columns for cell in col if cell)
    total = active * args.intensity
    print(f"  {active} active cells × {args.intensity} commits = {total} total commits")

    if args.dry_run:
        return

    # Collect dates
    start = get_start_sunday(args.year)
    dates = []
    for ci, col in enumerate(columns):
        for row in range(7):
            if col[row]:
                day = start + datetime.timedelta(days=((ci + offset) * 7 + row))
                dates.append(day)

    print(f"\n  Target year: {args.year} (starting from {start})")
    print(f"  Will create {total} commits across {len(dates)} days.\n")

    confirm = input("  Proceed? [y/N] ").strip().lower()
    if confirm != 'y':
        print("  Aborted.")
        return

    # Create temp repo and make commits
    tmpdir = tempfile.mkdtemp(prefix="gitgraffiti-")
    subprocess.run(["git", "init", "-q"], cwd=tmpdir, check=True)

    # Write a trackable file — GitHub is more reliable counting commits
    # with real file changes vs --allow-empty.
    log_path = os.path.join(tmpdir, "graffiti.log")
    with open(log_path, "w") as f:
        f.write("")
    subprocess.run(["git", "add", "graffiti.log"], cwd=tmpdir, check=True)

    # Push in small batches with delays to avoid GitHub rate limits.
    BATCH_SIZE = 200
    BATCH_DELAY = 15  # seconds between pushes
    commit_count = 0
    first_push = True

    if args.repo:
        subprocess.run(["git", "remote", "add", "origin", args.repo], cwd=tmpdir, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=tmpdir, check=True)

    for di, date in enumerate(dates):
        for i in range(args.intensity):
            hour = (i * 3) % 24
            minute = (i * 7) % 60
            ts = f"{date}T{hour:02d}:{minute:02d}:00"
            env = {**os.environ, "GIT_AUTHOR_DATE": ts, "GIT_COMMITTER_DATE": ts}

            # Write a real file change for each commit
            with open(log_path, "a") as f:
                f.write(f"{date} #{i}\n")
            subprocess.run(["git", "add", "graffiti.log"], cwd=tmpdir, check=True,
                           capture_output=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", f"gitgraffiti {date} #{i}"],
                cwd=tmpdir, env=env, check=True,
                capture_output=True,
            )
            commit_count += 1

            # Push in batches so GitHub processes all contributions
            if args.repo and commit_count % BATCH_SIZE == 0:
                push_flags = ["-uf"] if first_push else ["-u"]
                subprocess.run(
                    ["git", "push"] + push_flags + ["origin", "main"],
                    cwd=tmpdir, check=True, capture_output=True,
                )
                first_push = False
                sys.stdout.write(f"\r  Pushed batch ({commit_count}/{total} commits), waiting {BATCH_DELAY}s...")
                sys.stdout.flush()
                time.sleep(BATCH_DELAY)

        sys.stdout.write(f"\r  Committed: {date} ({di + 1}/{len(dates)})    ")
        sys.stdout.flush()
    print()

    if args.repo:
        # Push any remaining commits
        if commit_count % BATCH_SIZE != 0:
            push_flags = ["-uf"] if first_push else ["-u"]
            subprocess.run(
                ["git", "push"] + push_flags + ["origin", "main"],
                cwd=tmpdir, check=True,
            )
        print("  Done! Check your profile in a few minutes.")
        import shutil
        shutil.rmtree(tmpdir)
    else:
        print(f"\n  Commits ready in: {tmpdir}")
        print("  To push, run:")
        print(f"    cd {tmpdir}")
        print("    git remote add origin <your-repo-url>")
        print("    git push -u origin main --force")


if __name__ == "__main__":
    main()
