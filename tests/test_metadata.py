"""Metadata, build files and manifest agree with each other."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pensum

ROOT = Path(__file__).resolve().parent.parent
APP_ID = "de.nexumia.Pensum"


def test_version_matches_meson_and_metainfo():
    meson = (ROOT / "meson.build").read_text()
    assert re.search(r"version: '([^']+)'", meson).group(1) == pensum.VERSION
    metainfo = ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml")
    assert metainfo.find("releases/release").get("version") == pensum.VERSION


def test_every_module_and_data_file_is_installed():
    meson = (ROOT / "meson.build").read_text()
    for path in (ROOT / "pensum").rglob("*.py"):
        name = path.relative_to(ROOT).as_posix()
        assert f"'{name}'" in meson, name
    assert "'pensum/store/sp-defaults.json'" in meson
    assert "'pensum/style.css'" in meson


def test_phone_metadata():
    desktop = (ROOT / "data" / f"{APP_ID}.desktop").read_text()
    # Phosh matches the substring "mobile;" case-insensitively.
    assert re.search(r"^X-Purism-FormFactor=.*mobile;", desktop,
                     re.IGNORECASE | re.MULTILINE)
    root = ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml").getroot()
    length = root.find("recommends/display_length")
    assert length.get("compare") == "ge" and length.text == "360"
    assert {"touch", "pointing", "keyboard"} <= {
        c.text for c in root.findall("supports/control")}
    assert root.find("url[@type='donation']").text == pensum.SUPPORT_URL


def test_manifest_has_no_file_access_and_network_only_for_webdav():
    manifest = (ROOT / f"{APP_ID}.yml").read_text()
    args = [line.strip()[2:] for line in manifest.splitlines()
            if line.strip().startswith("- --")]
    assert not [a for a in args if a.startswith("--filesystem")]
    # The network is for reading a sync folder on WebDAV (#28): only that
    # module opens connections, and it sends nothing but GET.
    assert "--share=network" in args
    network = re.compile(r"^\s*(import|from)\s+(urllib|http|socket|ssl|requests)\b", re.M)
    users = {p.relative_to(ROOT).as_posix() for p in (ROOT / "pensum").rglob("*.py")
             if network.search(p.read_text())}
    assert users == {"pensum/sync/webdav.py"}
    webdav = (ROOT / "pensum/sync/webdav.py").read_text()
    assert re.findall(r'method="(\w+)"', webdav) == ["GET"]
    commit = re.search(r"- name: phosh-toolkit.*?commit: (\w+)", manifest, re.S)
    assert commit and len(commit.group(1)) == 40


def test_screenshot_actions_exist():
    release = (ROOT / "release.toml").read_text()
    main = (ROOT / "pensum" / "main.py").read_text()
    for action in re.findall(r'"app\.([a-z-]+)', release):
        assert f'"{action}"' in main, action


def test_stable_build_from_source_tree():
    assert pensum.APP_ID == APP_ID and not pensum.NIGHTLY
    assert pensum.VERSION_LABEL == pensum.VERSION
