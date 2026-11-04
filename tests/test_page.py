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


def test_diagnostic_versions_cannot_break_out_of_the_inline_script():
    body, headers = page.page(True, '</script><script>alert("version")</script>', 1)
    html = body.decode()
    assert html.count("<script>") == 1 and html.count("</script>") == 1
    script = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    assert f"script-src {_sha(script)};" in headers["Content-Security-Policy"]
    assert "{build}" not in script and r"\u003c/script>" in script


def test_signed_or_not_each_page_allows_exactly_its_own_script():
    for signed in (False, True):
        body, headers = page.page(signed)
        script = re.search(r"<script>(.*)</script>", body.decode(), re.S).group(1)
        assert f"script-src {_sha(script)};" in headers["Content-Security-Policy"]
        assert f"const SIGNED = {'true' if signed else 'false'};" in script
        assert ('"X-Sig": sign(url)' in script) and "{signed}" not in script


def test_the_page_signs_exactly_as_python_does():
    """Its SHA-256 / HMAC (http:// pages get no crypto.subtle) against hashlib, at
    every block-boundary length, in Node when it's there."""
    import hmac
    import json
    import secrets
    import shutil
    import subprocess

    import pytest
    node = shutil.which("node")
    if node is None:
        pytest.skip("no Node.js here")
    js = page.SCRIPT
    code = js[js.index("const K256"):js.index("function sign(")]
    cases = [("k", ""), ("key", "The quick brown fox jumps over the lazy dog"), ("k" * 100, "x")]
    cases += [(secrets.token_urlsafe(24), "é" + "x" * n) for n in (0, 54, 55, 62, 63, 64, 120, 999)]
    run = code + ("\nconst enc = (s) => new TextEncoder().encode(s);\n"
                  f"console.log(JSON.stringify({json.dumps(cases)}.map(([k, m]) => "
                  "b64url(hmac(enc(k), enc(m))))));")
    got = json.loads(subprocess.run([node, "-e", run], capture_output=True, text=True,
                                    check=True, timeout=180).stdout)   # a cold CI Node: slow
    want = [base64.urlsafe_b64encode(hmac.new(k.encode(), m.encode(), hashlib.sha256)
                                     .digest()).decode().rstrip("=") for k, m in cases]
    assert got == want


def test_it_is_called_onion_pocket_everywhere():
    html = page.page()[0].decode()
    assert "<title>Onion Pocket</title>" in html and "<h1>Onion <em>Pocket</em></h1>" in html
    assert 'apple-mobile-web-app-title" content="Onion Pocket"' in html


def test_it_warns_while_others_cannot_hear_and_says_what_else_changes_the_voice():
    """Green Live with nothing reaching others, and "off" with an AI voice on, both looked
    fine on the phone. An older board sends neither field: no warning, no note."""
    assert 'id="setupwarn"' in page.BODY and "st.setup_ok === false" in page.SCRIPT
    assert 'id="vother"' in page.BODY and '(st.voices_on || []).filter' in page.SCRIPT


def test_who_is_listening_offers_the_simple_modes_with_the_exact_list_as_a_fallback():
    """The exact list's notes say things like "Opus 64 kbps": only Advanced and older
    boards show that list."""
    assert 'mode?simple=' in page.SCRIPT and "m.simples || null" in page.SCRIPT
    assert '$("mode").hidden = pick !== "advanced"' in page.SCRIPT


def test_new_pad_and_voice_controls_use_only_actions_the_page_already_has():
    from onion_pocket import addon
    for used in ("stop?id=", "volume?set", "say?again=1", "&seconds=", "setup?tab="):
        assert used in page.SCRIPT or used == "volume?set"
    assert '"?set=" + v' in page.SCRIPT
    for action in ("stop", "volume", "radio_volume", "say", "voice", "setup", "mode"):
        assert action in addon.ACTIONS
