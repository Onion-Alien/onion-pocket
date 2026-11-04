# CLAUDE.md

Guidance for AI coding agents working in this repo.

## This repo is public

Everything here is published, like Onion Board and Onion Watch, history included:

- **Never write personal or machine-specific data** into the repo: user names, real
  names, e-mails, `C:\Users\<name>\…` paths, host names, IPs (other than
  `127.0.0.1`, and `192.0.2.1` in `lan.py`, a documentation address that is never
  on a real network), LAN details, names of the author's other projects or
  machines. Use `%APPDATA%`, `Path.home()`, `example.com`, placeholders.
- **Never commit secrets** or anything from `%APPDATA%\OnionBoard\` (config, keys,
  logs).
- **Never add binaries or third-party assets.** The QR codes are drawn in code;
  the screenshots in `docs/screenshots/` are made for this project from made-up
  sounds.
- New network access must be added to `SECURITY.md`. No telemetry.

Run `python scripts/check_sensitive.py` before committing. It's also the
pre-commit hook: `git config core.hooksPath .githooks`. Your own identifiers go in
`.sensitive-patterns` (git-ignored, in the main checkout: worktrees read it from there).
Without it only the built-in rules run, and the scanner says so.

## Commit times and merging

Every commit's author and committer time must be `+0000`: a local time zone in a public
repo says where the author lives.

- `git config core.hooksPath .githooks` (required) turns on the hooks: `post-commit` and
  `post-merge` re-stamp new commits in UTC, and `pre-push` refuses anything that isn't.
- CI's *Commit times in UTC* step fails a PR that has any.
- **Merge only with `sh scripts/merge_pr.sh N [--delete-branch]`**: never GitHub's merge
  (the `gh` merge command, the Merge button) or *Update branch*, which write the commit
  in your local time zone.
- A branch whose commits aren't UTC: `sh scripts/utc_fix.sh`, then
  `git push --force-with-lease`.
- Never rewrite history already pushed to `main`.

## Working in the code

- Checks: `.venv\Scripts\ruff check .` and `.venv\Scripts\python -m pytest`.
  Tests use Qt's offscreen platform and a stand-in host (`tests/fakehost.py`): no
  window, no server, no network.
- The add-on runs inside Onion Board, which has no pip: import only the standard
  library and PySide6 (QtCore, QtGui, QtWidgets). `scripts/build_module.py` refuses
  anything else.
- It reaches Onion Board only through the host (`onion_pocket/host.py`). Anything
  it needs from the app is added to the host on Onion Board's side
  (`soundboard/ui/settings/remotehost.py`) first, with `API_VERSION` raised when the
  contract changes.
- Never widen what a phone can do (`addon.ACTIONS`) beyond what README's *What your
  phone can do* lists (the mic switch, the voice changer and the replay were added
  with the author's say-so in 0.3.0), and never to the chat / alert actions, hearing
  the mic or anything that reads files, without the author's say-so.
- Don't launch Onion Board or anything that opens windows without asking first.
- Edit files with UTF-8-safe tools (Windows PowerShell 5.1 mangles UTF-8).
