"""The add-on zip (scripts/build_module.py): what Onion Board needs to install and
load it, nothing it doesn't ship, the same bytes every time."""
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_module  # noqa: E402


def test_the_zip_holds_the_manifest_licence_and_package(tmp_path):
    z = zipfile.ZipFile(build_module.build(tmp_path))
    names = z.namelist()
    assert names == sorted(names)
    assert {"onion-pocket/module.json", "onion-pocket/LICENSE",
            "onion-pocket/onion_pocket/__init__.py",
            "onion-pocket/onion_pocket/addon.py"} <= set(names)
    m = json.loads(z.read("onion-pocket/module.json"))
    from onion_pocket import __version__
    from onion_pocket.host import API_VERSION
    assert m["id"] == "onion-pocket" and m["kind"] == "remote"
    assert m["version"] == __version__ and m["api_version"] == API_VERSION
    assert m["package"] == "onion_pocket" and m["entry"] == "onion_pocket.addon"
    assert set(m["imports"]) <= build_module.ALLOWED


def test_the_same_source_builds_the_same_zip(tmp_path):
    a = build_module.build(tmp_path / "a").read_bytes()
    b = build_module.build(tmp_path / "b").read_bytes()
    assert a == b


def test_an_import_onion_board_does_not_ship_is_refused(tmp_path, monkeypatch):
    extra = tmp_path / "onion_pocket"
    extra.mkdir()
    (extra / "bad.py").write_text("import requests\n")
    monkeypatch.setattr(build_module, "package_files",
                        lambda: sorted((ROOT / "onion_pocket").glob("*.py")) + [extra / "bad.py"])
    try:
        build_module.build(tmp_path / "out")
    except SystemExit as e:
        assert "requests" in str(e)
    else:
        raise AssertionError("built with requests in it")
