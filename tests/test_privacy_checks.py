"""The checks that keep personal data out of this public repo, run for real on a throwaway
git repo: the hooks and scanner as they are in this checkout, a time zone and a private
word that must be refused."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORD = "zzprivateword"
LOCAL = "2026-01-02T03:04:05+1300"
pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="no git here")


def env(when=None):
    e = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@users.noreply.github.com",
             GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@users.noreply.github.com",
             PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
    for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        e.pop(k, None)
    if when:
        e.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    return e


def git(cwd, *args, when=None, check=True):
    return subprocess.run(["git", *args], cwd=cwd, env=env(when), capture_output=True, text=True,
                          check=check, timeout=60)


def commit(repo, name, when=None, check=True):
    (repo / name).write_text("x\n", encoding="utf-8")
    git(repo, "add", name)
    return git(repo, "commit", "-m", name, when=when, check=check)


def zones(repo, rev="HEAD"):
    return git(repo, "log", "-1", "--format=%ad %cd", "--date=format:%z", rev).stdout.split()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "core.autocrlf", "false")
    for sub in (".githooks", "scripts"):
        shutil.copytree(ROOT / sub, r / sub, ignore=shutil.ignore_patterns("__pycache__"))
    (r / ".gitignore").write_text(".sensitive-patterns\n", encoding="utf-8")
    (r / ".sensitive-patterns").write_text(WORD + "\n", encoding="utf-8")
    git(r, "add", "-A")
    git(r, "commit", "-m", "start", when="2026-01-01T00:00:00+0000")
    return r


def hooks_on(repo):
    git(repo, "config", "core.hooksPath", ".githooks")


def test_post_commit_stamps_a_new_commit_in_utc(repo):
    hooks_on(repo)
    commit(repo, "a", when=LOCAL)
    assert zones(repo) == ["+0000", "+0000"]


def test_post_merge_stamps_a_merge_in_utc(repo):
    hooks_on(repo)
    git(repo, "switch", "-c", "side")
    commit(repo, "a")
    git(repo, "switch", "main")
    commit(repo, "b")
    git(repo, "merge", "--no-ff", "-m", "merge", "side", when=LOCAL)
    assert zones(repo) == ["+0000", "+0000"]


def test_pre_push_refuses_a_time_zone_and_lets_utc_through(repo, tmp_path):
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    commit(repo, "local", when=LOCAL)            # (no hooks yet: it keeps its time zone)
    hooks_on(repo)
    pushed = git(repo, "push", "origin", "main", check=False)
    assert pushed.returncode != 0 and "Push refused" in pushed.stderr
    assert git(bare, "branch", "--list").stdout.strip() == ""
    git(repo, "reset", "-q", "--hard", "HEAD~1")
    commit(repo, "utc")
    assert git(repo, "push", "origin", "main", check=False).returncode == 0


def test_check_utc_names_the_commit_and_fails(repo):
    commit(repo, "local", when=LOCAL)
    out = subprocess.run(["sh", "scripts/check_utc.sh", "-1", "HEAD"], cwd=repo, env=env(),
                         capture_output=True, text=True)
    assert out.returncode != 0 and "+1300" in out.stdout + out.stderr


def test_pre_commit_blocks_a_private_word(repo):
    hooks_on(repo)
    (repo / "note.txt").write_text(f"made by {WORD}\n", encoding="utf-8")
    git(repo, "add", "note.txt")
    done = git(repo, "commit", "-m", "note", check=False)
    assert done.returncode != 0 and "Commit blocked" in done.stdout + done.stderr


def scan(cwd, *args):
    return subprocess.run([sys.executable, "scripts/check_sensitive.py", *args], cwd=cwd, env=env(),
                          capture_output=True, text=True, timeout=120)


def test_a_worktree_uses_the_main_checkouts_private_patterns(repo, tmp_path):
    tree = tmp_path / "tree"
    git(repo, "worktree", "add", "-q", str(tree), "-b", "work")
    assert not (tree / ".sensitive-patterns").exists()
    (tree / "note.txt").write_text(f"made by {WORD}\n", encoding="utf-8")
    found = scan(tree)
    assert found.returncode == 1 and "note.txt" in found.stdout


def test_history_range_scans_only_those_commits(repo):
    commit(repo, "clean")
    (repo / "note.txt").write_text(f"made by {WORD}\n", encoding="utf-8")
    git(repo, "add", "note.txt")
    git(repo, "commit", "-m", "note")
    assert scan(repo, "--history=HEAD~1..HEAD").returncode == 1
    assert scan(repo, "--history=HEAD~2..HEAD~1").returncode == 0
