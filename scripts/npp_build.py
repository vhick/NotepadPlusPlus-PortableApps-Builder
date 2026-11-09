#!/usr/bin/env python3
"""Official Notepad++ portable x64 downloader, verifier, and PortableApps stage builder.
No third-party Python dependencies. Windows CI calls this after compiling launcher.
"""
from __future__ import annotations
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

REPO = "notepad-plus-plus/notepad-plus-plus"
BASE = "https://api.github.com/repos/" + REPO
STABLE_TAG = re.compile(r"^v?(\d+(?:\.\d+){2,3})$")
ASSET_RE = re.compile(r"^npp\.(\d+(?:\.\d+){2,3})\.portable\.x64\.zip$", re.I)
APP_ID = "NotepadPlusPlusCommunityPortable"
ROOT = "NotepadPlusPlusPortable"
BUILDER = "b1r2"


def semver(version: str) -> tuple[int, ...]:
    m = STABLE_TAG.fullmatch(version.strip())
    if not m:
        raise ValueError(f"Not a suitable stable Notepad++ version: {version}")
    return tuple(map(int, m.group(1).split(".")))


def gh_request(url: str) -> bytes:
    if not url.startswith(("https://api.github.com/", "https://github.com/", "https://objects.githubusercontent.com/", "https://release-assets.githubusercontent.com/")):
        raise ValueError("Untrusted download URL: " + url)
    headers = {"User-Agent": "NppPortableBuilder/1.0", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = "Bearer " + token
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=120) as response:
            final = response.geturl()
            if not final.startswith("https://"):
                raise ValueError("Non-HTTPS redirect forbidden: " + final)
            return response.read()
    except HTTPError as e:
        detail = e.read(250).decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url}: HTTP {e.code}: {detail}") from e
    except URLError as e:
        raise RuntimeError(f"Download failed: {url}: {e}") from e


def gh_json(url: str):
    return json.loads(gh_request(url).decode("utf-8"))


def get_release(version: str) -> dict:
    if version.strip():
        tag = "v" + ".".join(str(n) for n in semver(version))
        release = gh_json(BASE + "/releases/tags/" + tag)
        if release.get("draft") or release.get("prerelease"):
            raise RuntimeError("Requested version is not stable")
        return release
    found: list[dict] = []
    for page in range(1, 8):
        releases = gh_json(BASE + f"/releases?per_page=100&page={page}")
        if not isinstance(releases, list):
            raise RuntimeError("GitHub release API did not return an array")
        for release in releases:
            if release.get("draft") or release.get("prerelease"):
                continue
            if STABLE_TAG.fullmatch(release.get("tag_name", "")):
                found.append(release)
        if len(releases) < 100:
            break
    if not found:
        raise RuntimeError("No numeric stable release found")
    return max(found, key=lambda r: semver(r["tag_name"]))


def dereference_tag(tag: str) -> str:
    ref = gh_json(BASE + "/git/ref/tags/" + tag)
    obj = ref["object"]
    for _ in range(3):
        sha = obj.get("sha", "")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
            raise RuntimeError("Unable to verify upstream source commit")
        if obj.get("type") == "commit":
            return sha.lower()
        if obj.get("type") != "tag":
            raise RuntimeError("Unexpected GitHub tag target")
        obj = gh_json(BASE + "/git/tags/" + sha)["object"]
    raise RuntimeError("Tag recursion unexpectedly deep")


def parse_checksum(data: bytes, asset_name: str) -> str | None:
    name = re.escape(asset_name)
    for line in data.decode("utf-8-sig", errors="replace").splitlines():
        m = re.fullmatch(r"\s*([0-9a-fA-F]{64})\s+\*?(?:\./)?" + name + r"\s*", line)
        if m:
            return m.group(1).lower()
    return None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def secure_extract(z: zipfile.ZipFile, dest: Path):
    entries = z.infolist()
    if len(entries) > 4000:
        raise ValueError("Unexpected number of files in upstream archive")
    total = 0
    for member in entries:
        name = member.filename.replace("\\", "/")
        p = PurePosixPath(name)
        if (not name or name.startswith("/") or ".." in p.parts or
            ":" in name or name.startswith("\\\\") or "\x00" in name):
            raise ValueError("Unsafe upstream ZIP entry: " + name)
        if (member.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError("Upstream ZIP contains symbolic links: " + name)
        total += member.file_size
        if total > 500 * 1024 * 1024:
            raise ValueError("Expanded upstream archive unexpectedly large")
    z.extractall(dest)


def pe_machine(path: Path) -> int:
    with path.open("rb") as f:
        b = f.read(64)
        if len(b) != 64 or b[:2] != b"MZ":
            raise ValueError("Not an actual PE executable: " + str(path))
        f.seek(struct.unpack_from("<I", b, 60)[0])
        if f.read(4) != b"PE\0\0":
            raise ValueError("PE header missing in " + str(path))
        raw = f.read(2)
        if len(raw) != 2:
            raise ValueError("Truncated machine field: " + str(path))
        return struct.unpack("<H", raw)[0]


def package_version(v: str) -> str:
    parts = list(semver(v))
    return ".".join(map(str, (parts + [0, 0, 0, 0])[:4]))


def write_appinfo(path: Path, version: str, revision: str):
    value = f"""[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=Notepad++ Portable Community
AppID={APP_ID}
Publisher=Don Ho and Notepad++ contributors (unofficial repackaging)
Homepage=https://notepad-plus-plus.org/
Category=Development
Description=Notepad++ text and code editor with package-local settings
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion={package_version(version)}
DisplayVersion={version} Community {revision}

[Control]
Icons=1
Start=NotepadPlusPlusPortable.exe
"""
    path.write_text(value, encoding="utf-8", newline="\n")


def copy_packaged_icons(exe: Path, appinfo: Path):
    """Extract legally usable app artwork from the verified official executable; no invented icons."""
    if os.name != "nt":
        raise RuntimeError("Real Windows icon extraction requires the Windows hosted runner")
    script = Path(__file__).with_name("extract_icons.ps1")
    run = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File", str(script), "-Exe", str(exe), "-Out", str(appinfo)],
                         capture_output=True, text=True, encoding="utf-8")
    if run.returncode:
        raise RuntimeError("Authentic icon extraction failed: " + (run.stderr or run.stdout))
    for file in ["appicon.ico", "appicon_16.png", "appicon_32.png"]:
        if not (appinfo / file).is_file():
            raise RuntimeError("Icon missing after extraction: " + file)


def create_zip(source: Path, target: Path):
    """Deterministic ZIP metadata; no filesystem timestamps, keep empty directories."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7, allowZip64=True) as z:
        for entry in sorted([source] + list(source.rglob("*"))):
            if entry.is_symlink():
                raise ValueError("Symlink in staged package: " + str(entry))
            arc = entry.relative_to(source.parent).as_posix()
            info = zipfile.ZipInfo(arc + ("/" if entry.is_dir() else ""), date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o40755 if entry.is_dir() else 0o100644) << 16
            info.compress_type = zipfile.ZIP_STORED if entry.is_dir() else zipfile.ZIP_DEFLATED
            if entry.is_dir():
                z.writestr(info, b"")
            else:
                with entry.open("rb") as src, z.open(info, "w", force_zip64=True) as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
    with zipfile.ZipFile(target) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError("Generated ZIP checksum failure: " + bad)



def normalize_portable_marker(marker: Path, attribution: Path) -> dict:
    """Preserve an upstream nonempty marker and normalize only the staged copy.

    The official Notepad++ docs define doLocalConf.xml as a zero-byte mode flag.
    Never edit the SHA-256-verified upstream archive or existing user Data.
    """
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise ValueError("Invalid upstream portable marker type: " + str(marker))
    if not marker.exists():
        marker.write_bytes(b"")
        return {"status": "created-empty-marker", "source_size": 0}
    size = marker.stat().st_size
    if size == 0:
        return {"status": "preserved-empty-marker", "source_size": 0}
    if size > 1024 * 1024:
        raise ValueError("Unexpectedly large upstream portable marker: " + str(size))
    original = marker.read_bytes()
    original_sha = hashlib.sha256(original).hexdigest()
    attribution.mkdir(parents=True, exist_ok=True)
    saved = attribution / "upstream-doLocalConf.xml.original"
    if saved.exists():
        raise ValueError("Source marker evidence would overwrite a staged file")
    saved.write_bytes(original)
    if sha256(saved) != original_sha:
        raise RuntimeError("Saved upstream portable-marker verification failed")
    marker.write_bytes(b"")
    if marker.stat().st_size != 0:
        raise RuntimeError("Failed to create zero-byte staged portable marker")
    return {"status": "normalized-to-empty", "source_size": size,
            "source_sha256": original_sha,
            "source_backup": "Other/Source/upstream-doLocalConf.xml.original"}


def validate_package(root: Path, zip_path: Path, version: str):
    mainexe = root / "App" / "Notepad++" / "notepad++.exe"
    launcher = root / "NotepadPlusPlusPortable.exe"
    for file in (mainexe, launcher, root / "App" / "AppInfo" / "appinfo.ini",
                 root / "App" / "AppInfo" / "appicon.ico",
                 root / "App" / "AppInfo" / "appicon_16.png",
                 root / "App" / "AppInfo" / "appicon_32.png",
                 root / "App" / "Notepad++" / "doLocalConf.xml"):
        if not file.is_file():
            raise ValueError("Required package file missing: " + str(file))
    if pe_machine(mainexe) != 0x8664 or pe_machine(launcher) != 0x8664:
        raise ValueError("x64 PE architecture validation failed")
    if (root / "App" / "Notepad++" / "doLocalConf.xml").stat().st_size != 0:
        raise ValueError("Portable mode marker must be exactly zero bytes")
    ini = configparser.ConfigParser(interpolation=None)
    ini.read(root / "App" / "AppInfo" / "appinfo.ini", encoding="utf-8")
    if ini["Details"]["AppID"] != APP_ID or ini["Control"]["Start"] != launcher.name:
        raise ValueError("AppInfo identity/entry mismatch")
    if ini["Version"]["PackageVersion"] != package_version(version):
        raise ValueError("AppInfo version mismatch")
    for png in ("appicon_16.png", "appicon_32.png"):
        if (root / "App" / "AppInfo" / png).read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Invalid PNG icon: " + png)
    if (root / "App" / "AppInfo" / "appicon.ico").read_bytes()[:4] != b"\x00\x00\x01\x00":
        raise ValueError("Invalid ICO header")
    if not (root / "Data" / "Settings").is_dir() or not (root / "Other" / "Source").is_dir():
        raise ValueError("Missing persistent-data/attribution folders")
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        for expected in [f"{ROOT}/NotepadPlusPlusPortable.exe", f"{ROOT}/App/Notepad++/notepad++.exe",
                         f"{ROOT}/App/AppInfo/appinfo.ini", f"{ROOT}/Data/Settings/", f"{ROOT}/Other/Source/PROVENANCE.json"]:
            if expected not in names:
                raise ValueError("ZIP layout missing: " + expected)
        if z.testzip() is not None:
            raise ValueError("Corrupt ZIP content")
    return True


def build(args):
    revision = args.revision
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,30}", revision):
        raise ValueError("Revision must be alphanumeric, may include ._- and start with a letter")
    release = get_release(args.version)
    tag = release["tag_name"]
    v = STABLE_TAG.fullmatch(tag).group(1)
    commit = dereference_tag(tag)
    exact = f"npp.{v}.portable.x64.zip"
    checksum_name = f"npp.{v}.checksums.sha256"
    assets = {a["name"]: a for a in release.get("assets", [])}
    if exact not in assets or checksum_name not in assets:
        raise RuntimeError("Official upstream x64 portable ZIP or checksums missing for " + tag)
    official_checksums = gh_request(assets[checksum_name]["browser_download_url"])
    expected = parse_checksum(official_checksums, exact)
    from_notes = parse_checksum(release.get("body", "").encode("utf-8"), exact)
    api_digest = assets[exact].get("digest")
    if not expected or (from_notes and from_notes != expected) or (api_digest and api_digest.lower() != "sha256:" + expected):
        raise RuntimeError("Official SHA-256 sources are missing or disagree")
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    upstream = work / exact
    if not upstream.exists() or sha256(upstream) != expected:
        if upstream.exists():
            upstream.unlink()
        upstream.write_bytes(gh_request(assets[exact]["browser_download_url"]))
    if sha256(upstream) != expected:
        upstream.unlink(missing_ok=True)
        raise RuntimeError("Downloaded Notepad++ archive SHA256 MISMATCH")
    stage = work / "stage" / ROOT
    if stage.exists():
        shutil.rmtree(stage)
    appdir = stage / "App" / "Notepad++"
    appdir.mkdir(parents=True)
    with zipfile.ZipFile(upstream) as z:
        secure_extract(z, appdir)
    # All real release binaries are preserved; do not assume GUP/Plugins Admin is unnecessary.
    if not (appdir / "notepad++.exe").exists():
        raise RuntimeError("Official ZIP did not contain root-level notepad++.exe")
    if pe_machine(appdir / "notepad++.exe") != 0x8664:
        raise RuntimeError("Official Notepad++ release is not x64")
    marker = appdir / "doLocalConf.xml"
    marker_evidence = normalize_portable_marker(marker, stage / "Other" / "Source")
    print("Upstream portable marker (staged copy only):", json.dumps(marker_evidence), flush=True)
    # Fresh profile is ALWAYS Data. No defaults are copied on upgrades.
    for folder in ["Settings", "PluginConfig", "PluginsBackup", "LegacyIniBackup", "Recovery/Conflicts"]:
        (stage / "Data" / folder).mkdir(parents=True, exist_ok=True)
    (stage / "Other" / "Source").mkdir(parents=True)
    shutil.copy2(args.launcher, stage / "NotepadPlusPlusPortable.exe")
    if pe_machine(stage / "NotepadPlusPlusPortable.exe") != 0x8664:
        raise RuntimeError("Launcher is not a genuine Windows x64 PE")
    appinfo = stage / "App" / "AppInfo"
    appinfo.mkdir(parents=True)
    write_appinfo(appinfo / "appinfo.ini", v, revision)
    copy_packaged_icons(appdir / "notepad++.exe", appinfo)
    # The shared installer preserves Data but REPLACES the entire App directory.
    # The launcher backs up plug-ins and configuration into Data on every complete exit.
    (stage / "Other" / "Source" / "README.txt").write_text(
        "UNOFFICIAL community package, not an official PortableApps.com release.\n"
        "Notepad++ upstream: https://github.com/notepad-plus-plus/notepad-plus-plus\n"
        "Original upstream source is GPL-3.0-or-later. Check upstream file notices and plugin licenses.\n"
        "Launcher source is distributed under MIT (see MIT-LAUNCHER.txt).\n"
        "Before upgrading, exit Notepad++ through this launcher to save plug-in state.\n"
        "Keep the Data directory when upgrading or rolling back.\n", encoding="utf-8")
    kitsrc = Path(__file__).resolve().parents[1]
    shutil.copy2(kitsrc / "licenses" / "GPL-3.0.txt", stage / "Other" / "Source" / "GPL-3.0.txt")
    shutil.copy2(kitsrc / "licenses" / "MIT-LAUNCHER.txt", stage / "Other" / "Source" / "MIT-LAUNCHER.txt")
    identity = {
        "source_repo": REPO, "source_tag": tag, "source_commit": commit,
        "portable_asset": exact, "portable_asset_sha256": expected,
        "builder_revision": revision, "builder_commit": os.getenv("GITHUB_SHA", "local-uncommitted"),
        "launcher_sha256": sha256(stage / "NotepadPlusPlusPortable.exe"),
        "package_version": package_version(v), "architecture": "win-x64",
        "compiler_sdk": os.getenv("DOTNET_SDK_VERSION", "unknown"),
        "installer_engine": "custom-nsis", "data_strategy": "-settingsDir Data/Settings plus package-local plugin backup",
        "notes": "Source binary is official developer portable ZIP, NOT rebuilt from source",
        "portable_marker": marker_evidence,
    }
    (stage / "Other" / "Source" / "PROVENANCE.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    zip_path = output / f"{ROOT}_{v}_{revision}_win-x64.zip"
    if zip_path.exists():
        zip_path.unlink()
    create_zip(stage, zip_path)
    validate_package(stage, zip_path, v)
    result = {"version": v, "tag": tag, "commit": commit, "release_tag": f"portable-npp-v{v}-c{commit[:8]}-{revision}",
              "zip_name": zip_path.name, "zip_path": str(zip_path), "zip_sha256": sha256(zip_path),
              "stage_dir": str(stage), "sha256_asset": expected, "builder_revision": revision}
    (work / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / (zip_path.name + ".sha256")).write_text(f"{result['zip_sha256']}  {zip_path.name}\n", encoding="ascii")
    print("BUILT AND STATIC-VALIDATED:", json.dumps(result, indent=2), flush=True)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="", help="Stable release version; blank=latest numeric stable")
    ap.add_argument("--work", default="build")
    ap.add_argument("--output", default="dist")
    ap.add_argument("--launcher", required=True)
    ap.add_argument("--revision", default=BUILDER)
    a = ap.parse_args()
    build(a)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("BUILD FAILED:", str(e), file=sys.stderr)
        raise
