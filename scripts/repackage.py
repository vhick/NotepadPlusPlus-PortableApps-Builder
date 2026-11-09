#!/usr/bin/env python3
"""Packaging-only: verify a prior publisher release ZIP and stage it WITHOUT rebuilding upstream.
The ZIP and its source/launcher identity are retained byte-for-byte in a new tagged release.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile
from npp_build import APP_ID, ROOT, sha256, secure_extract, validate_package

ap=argparse.ArgumentParser()
ap.add_argument('--zip',required=True)
ap.add_argument('--checksums',required=True)
ap.add_argument('--work',default='build')
ap.add_argument('--output',default='dist')
ap.add_argument('--revision',required=True)
a=ap.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_.-]{1,30}',a.revision):
    raise SystemExit('Invalid packaging-only revision')
p=Path(a.zip).resolve(); sums=Path(a.checksums).read_text(encoding='utf-8-sig')
match=re.search(r'(?m)^([0-9a-fA-F]{64})\s+\*?'+re.escape(p.name)+r'\s*$',sums)
if not match or sha256(p)!=match.group(1).lower():
    raise SystemExit('Publisher release checksums missing or changed: '+p.name)
work=Path(a.work).resolve(); out=Path(a.output).resolve()
stage=work/'repackage-stage'/ROOT
if stage.exists():shutil.rmtree(stage)
stage.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(p) as z:
    names=z.namelist()
    if not names or any(not n.startswith(ROOT+'/') for n in names):
        raise SystemExit('ZIP does not have precisely the expected portable root')
    secure_extract(z,stage.parent)
meta=json.loads((stage/'Other'/'Source'/'PROVENANCE.json').read_text(encoding='utf-8'))
v=meta['source_tag'].removeprefix('v')
if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,30}', meta['builder_revision']) or meta['architecture']!='win-x64':
    raise SystemExit('Unknown builder source identity; refuse repackaging')
validate_package(stage,p,v)
out.mkdir(parents=True,exist_ok=True)
dest=out/p.name
if dest.exists():dest.unlink()
shutil.copy2(p,dest)
if sha256(dest)!=sha256(p):raise SystemExit('Copy SHA mismatch')
result={'version':v, 'source_commit':meta['source_commit'], 'zip_name':dest.name,
        'zip_sha256':sha256(dest),'stage_dir':str(stage),
        'tag':'portable-npp-v'+v+'-c'+meta['source_commit'][:8]+'-'+meta['builder_revision']+'-repack-'+a.revision,'packaging_revision':a.revision}
(work/'repackage-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('VERIFIED PREVIOUS ZIP AND SOURCE IDENTITY:',json.dumps(result,indent=2))
