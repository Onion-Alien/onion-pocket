"""The phone page (onion_pocket/page.py): locked down by a hash-only policy that
matches the script and style it really holds, names put in as text only."""
import base64
import hashlib
import re

from onion_pocket import page


def _sha(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def test_the_policy_allows_exactly_its_own_script_and_style():
    body, headers = page.page()
    html = body.decode()
    csp = headers["Content-Security-Policy"]
    script = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    style = re.search(r"<style>(.*)</style>", html, re.S).group(1)
    assert f"script-src {_sha(script)};" in csp and f"style-src {_sha(style)};" in csp
    assert "default-src 'none'" in csp and "connect-src 'self'" in csp
    assert "unsafe-inline" not in csp and "frame-ancestors 'none'" in csp
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Cache-Control"] == "no-store"


def test_nothing_loads_from_anywhere_else():
    html = page.page()[0].decode()
    assert "{script}" not in html and "{style}" not in html
    assert not re.search(r"""(src|href)=["']?https?:""", html)
    assert 'style="' not in page.BODY                       # the policy is hash-only


def test_names_go_in_as_text_never_markup():
    """Sound names come from files and web titles: the script never parses them."""
    assert "innerHTML" not in page.SCRIPT and "insertAdjacentHTML" not in page.SCRIPT
    assert "textContent = s.name" in page.SCRIPT
    assert "/^#[0-9a-fA-F]{3,8}$/" in page.SCRIPT           # colours are checked first


def test_the_key_leaves_the_address_bar():
    assert "history.replaceState" in page.SCRIPT and '"X-Token": key' in page.SCRIPT
