# SimpleCrawler

A minimal, polite Python web crawler boilerplate.

Features
- Respects `robots.txt` when available
- Delay between requests
- Optional same-domain restriction

Quickstart

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the crawler:

```bash
python main.py https://example.com --max-pages 10 --max-depth 1 --delay 0.5 --output out.json --same-domain
```

Files
- `crawler.py`: crawler implementation
- `main.py`: simple CLI entry point

Git hooks

To enable an optional pre-commit hook that auto-applies allowed updates from the `updates/` folder and stages them:

1. Set the repository hooks path:

```bash
git config core.hooksPath .githooks
```

2. Edit `allowed_files.json` to list the relative file paths the hook is allowed to overwrite.

3. Place replacement files under the `updates/` directory with the same relative paths.

4. On commit, the hook will copy files from `updates/` to the working tree and run `git add` so your commit includes them.

The auto-apply logic lives in `hooks/auto_apply.py`.

Notes
- This is a starting point. Add error handling, politeness, concurrency, or persistence as needed.
