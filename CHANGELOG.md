# Builder changelog

## b1r3 — 2026-11-09

**Commit summary:** `Fix Notepad++ PortableApps Source staging collision (b1r3)`

- Fix Windows `FileExistsError [WinError 183]` at `scripts/npp_build.py:344` by reusing the already-created `Other/Source` directory.
- Preserve original upstream `doLocalConf.xml` backup and provenance, without deleting or reinitializing package/user data.
- Add offline end-to-end fixture test for nonempty marker normalization, Source directory reuse, staged ZIP integrity, empty folder inclusion and deterministic rebuilds.
- Bump workflow's default package revision to `b1r3` and update documentation.
- Keep pinned shared installer `vhick/Portable-Package-Builder@v1.0.0` and publisher `vhick/portable-release-publisher@v1.1.1` unchanged.

**Evidence:** prior b1r2 run compiled the Windows launcher and normalized marker; current b1r3 static checks and controlled fixture tests passed. b1r3 hosted Windows CI and interactive application tests have not been run.

## b1r2 — 2026-11-09

- Preserve upstream nonempty `doLocalConf.xml` as immutable evidence in staging, normalize staged marker to zero bytes, and add regression tests.

## b1r1 — 2026-11-09

- Initial builder source kit, launcher, resolver, packaging and publishing automation.
