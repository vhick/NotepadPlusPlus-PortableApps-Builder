#!/usr/bin/env python3
"""Independent static NSIS output checks; not a claim that GUI installation was tested."""
from __future__ import annotations
import argparse, hashlib, os
from pathlib import Path
import subprocess
import sys
from npp_build import pe_machine

ap=argparse.ArgumentParser()
ap.add_argument("--installer",required=True)
a=ap.parse_args()
p=Path(a.installer).resolve()
if not p.is_file() or not p.name.endswith(".paf.exe"):
    raise SystemExit("Expected a real .paf.exe installer output")
if pe_machine(p) not in [0x14c,0x8664]:
    raise SystemExit("Unsupported installer PE format")
seven=next((q for q in ["C:/Program Files/7-Zip/7z.exe","C:/Program Files (x86)/7-Zip/7z.exe"] if Path(q).exists()),None)
if not seven:
    from shutil import which
    seven=which("7z") or which("7za")
if not seven:
    raise SystemExit("7-Zip missing; independent installer archive verification unavailable")
for params in [["t","-bso0","-bsp0",str(p)],["l",str(p)]]:
    res=subprocess.run([seven,*params],capture_output=True,text=True,encoding="utf-8",errors="replace")
    if res.returncode:
        raise SystemExit(f"7-Zip failed: {res.stderr or res.stdout}")
    if params[0]=="l":
        # Not a GUI-install test. Verify recognizable contents in the embedded NSIS archive.
        for wanted in ("notepad++.exe","appinfo.ini","NotepadPlusPlusPortable.exe"):
            if wanted.lower() not in res.stdout.lower():
                raise SystemExit("Installer archive missing payload member: "+wanted)
h=hashlib.sha256(p.read_bytes()).hexdigest()
sidecar=Path(str(p)+".sha256")
if sidecar.is_file() and h not in sidecar.read_text(encoding="ascii").lower():
    raise SystemExit("Installer SHA256 sidecar mismatch")
print("STATIC-VALIDATED installer",p.name,"SHA256",h,"; GUI install and upgrade NOT YET VERIFIED")
