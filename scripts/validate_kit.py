"""Check documented contracts and workflow integration offline without fake PE builds."""
from pathlib import Path
import re,sys
base=Path(__file__).resolve().parents[1]
files=[
    ".github/workflows/build-portableapps.yml",".github/workflows/repackage-only.yml","launcher/NotepadPlusPlusPortable.csproj",
    "launcher/Program.cs","scripts/npp_build.py","scripts/verify_shared_actions.py",
    "scripts/extract_icons.ps1","scripts/validate_installer.py","scripts/repackage.py","README.md",
    "docs/ACCEPTANCE.md","docs/AUDIT.md","docs/DATA-SAFETY.md","docs/STATUS.md",
    "licenses/GPL-3.0.txt","licenses/MIT-LAUNCHER.txt","CHANGELOG.md",
]
for x in files:
    if not (base/x).is_file():raise RuntimeError("Missing kit file: "+x)
workflow=(base/files[0]).read_text(encoding="utf-8")
for x in ["workflow_dispatch", "windows-2022", "Portable-Package-Builder@v1.0.0", "portable-release-publisher@v1.1.1", "dry-run: 'true'", "dry-run: 'false'", "contents: write"]:
    if x not in workflow:raise RuntimeError("Workflow contract missing: "+x)
source=(base/"launcher/Program.cs").read_text(encoding="utf-8")
for x in ["Environment.ProcessPath", "-settingsDir=", "doLocalConf.xml", "-multiInst", "PluginsBackup", "IsReparse", "MergeTree"]:
    if x not in source:raise RuntimeError("Launcher contract missing: "+x)
for name in ["*.dll", "*.exe"]:
    if list(base.rglob(name)):raise RuntimeError("Builder kit must not ship precompiled binaries")
print("STATIC-VALIDATED builder kit sources, workflow references and directory tree")
