#!/usr/bin/env python3
"""Fail-closed action interface/tag guard, revisited on every CI run."""
import json, os, re
from urllib.request import Request, urlopen
from pathlib import Path

ACTIONS = [
    ("vhick/Portable-Package-Builder", "v1.0.0", "0112c35", ["source-dir", "output-dir", "engine", "running-exe", "timeout-seconds", "package-revision", "official-tool-url", "official-tool-sha256"], ["installer-file", "installer-sha256", "app-id", "app-version"]),
    ("vhick/portable-release-publisher", "v1.1.1", "cb64f86", ["files", "tag", "release-title", "tag-prefix", "keep-releases", "prune", "dry-run"], []),
]

def read(url):
    headers = {"User-Agent":"Npp-PortableApps-Builder", "Accept":"application/vnd.github+json"}
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers),timeout=60) as r:
        if not r.geturl().startswith("https://"):
            raise RuntimeError("Untrusted non-HTTPS redirect")
        return r.read().decode("utf-8")

def verify():
    found=[]
    for repo,tag,prefix,inputs,outputs in ACTIONS:
        api="https://api.github.com/repos/"+repo
        ref=json.loads(read(api+"/git/ref/tags/"+tag))["object"]
        for _ in range(3):
            if ref["type"]=="commit": break
            if ref["type"]!="tag": raise RuntimeError("Unknown ref type for "+repo)
            ref=json.loads(read(api+"/git/tags/"+ref["sha"]))["object"]
        sha=ref["sha"].lower()
        if len(sha)!=40 or not sha.startswith(prefix):
            raise RuntimeError("Pinned tag commit unexpectedly changed: "+repo+" "+sha)
        yml=read("https://raw.githubusercontent.com/"+repo+"/"+sha+"/action.yml")
        for key in inputs:
            if not re.search(r"(?m)^  " + re.escape(key) + r":\s*$", yml):
                raise RuntimeError("Missing action input "+repo+" "+key)
        for key in outputs:
            if not re.search(r"(?m)^  " + re.escape(key) + r":\s*$", yml):
                raise RuntimeError("Missing action output "+repo+" "+key)
        if "using: composite" not in yml: raise RuntimeError("Action shape changed: "+repo)
        found.append({"repository":repo,"tag":tag,"commit":sha,"verified_action_yml":True,"inputs":inputs,"outputs":outputs})
    Path("build").mkdir(exist_ok=True)
    Path("build/shared_actions.json").write_text(json.dumps(found,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(found,indent=2))

if __name__=="__main__": verify()
