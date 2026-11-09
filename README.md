# Notepad++ PortableApps Builder b1r3 (unofficial)

**Selected mode: PORTABLEAPPS ONLY.** This is a complete builder *source kit*, not a precompiled Notepad++ application. It creates an x64 Notepad++ PortableApps-format ZIP and a **custom-NSIS PortableApps-style** `.paf.exe` installer on an unattended GitHub-hosted Windows runner. The installed shared actions remain pinned at `vhick/Portable-Package-Builder@v1.0.0` and `vhick/portable-release-publisher@v1.1.1`. The workflow independently checks each tagged commit's `action.yml` before using it. It never claims PortableApps.com certification.

**Notepad++ is fetched from its official developer's versioned portable x64 ZIP.** No unsupported source build is substituted. Stable version resolution is numeric, rejects prereleases, resolves the official release tag to the 40-character source commit, and checks the upstream checksum asset against the developer-published asset hash (plus release notes/API when present).

## Beginner-friendly GitHub Desktop setup

1. Sign into GitHub and create a **NEW EMPTY repository** named for example `NotepadPlusPlus-PortableApps-Builder`. Do **not** fork the Notepad++ upstream repository. Choose **Public** or **Private**. A private builder repository should stay private if your build outputs need to remain private.
2. Open GitHub Desktop and select **File > Clone repository**. Clone the new repository. Do not run `git init` manually.
3. Extract **the entire contents** of this builder kit ZIP *into the root* of the cloned repository. This includes the hidden `.github/workflows/build-portableapps.yml` folder. Do not put the kit within an extra nested folder.
4. In GitHub Desktop, inspect the changes, write a commit message (for example `Fix Notepad++ PortableApps staging when Source exists (b1r3)`), select **Commit to main**, then **Push origin**.
5. Open the builder repository on github.com, select **Actions > Build Notepad++ PortableApps x64 > Run workflow**. Leave `version` empty for the most recent stable release, or enter `8.9.9` (or another suitable stable upstream version). Leave `revision` at `b1r3` for this updated kit, but increase it if you update any builder code or the compiler. Keep `publish` checked to create a GitHub Release after static verification, or uncheck it for a test build without publication.
6. Review the job logs. Verify stages: **pinned actions**, **real native AOT launcher compilation**, **official Notepad++ SHA-256**, **ZIP validation**, **shared NSIS installer**, **installer static validation**, **publisher dry-run**, then **publication**.
7. Once successful, go to **Releases** on your builder repository (not Notepad++'s). Locate `portable-npp-v<UPSTREAM_VERSION>-c<SOURCE_SHA8>-b1r3`. Download both `NotepadPlusPlusPortable_<version>_b1r3_win-x64.zip` and, optionally, the `.paf.exe`. Compare their SHA-256 values to the release's `SHA256SUMS.txt` using PowerShell: `Get-FileHash -Algorithm SHA256 "your-file.zip"`.
8. Extract the ZIP keeping the **NotepadPlusPlusPortable** folder intact, preferably under your `PortableApps` directory or a writable USB drive. **Or** run the community `.paf.exe` installer, choose a writable folder, and refresh the PortableApps Platform menu.
9. Run the genuine compiled **`NotepadPlusPlusPortable.exe`** from the folder root, **not** `App\Notepad++\notepad++.exe` (which bypasses the launcher and recovery lifecycle). You can pass a filename from the command line. Do not open multiple copies of the same portable package; the launcher prevents conflicting concurrent sessions.
10. When upgrading, **close Notepad++ completely using the launcher**, back up **the entire `NotepadPlusPlusPortable` folder**, and install/extract the new package into the same location **without replacing `Data`**. The shared NSIS installer preserves `Data` by design but replaces `App`/`Other` and the root launcher. For ZIP upgrades, copy the new `App`, `Other` and root launcher into the existing directory, leaving `Data` untouched. Do **not** delete it. For rollback, use your prior package plus the *backup of its matching Data directory*, since configuration schema changes may make old versions incompatible.

For a **packaging-only retry** without downloading or rebuilding Notepad++, use **Actions > Repackage existing validated Notepad++ ZIP**. Supply an existing release tag from your *own builder repository*, a fresh `installer_revision` such as `re2`, and choose whether to publish. It downloads a ZIP and publisher SHA256SUMS from the existing verified release, confirms the source identity and staged layout, and runs only the pinned shared installer/publisher. The original ZIP bytes are retained.

The builder generates the artifacts in `dist/` on CI; generated archives are not committed to Git. On installer generation failure, the independently validated ZIP is uploaded as a short-lived workflow artifact, while publication is stopped and the job fails.

## Runtime folder layout

```text
NotepadPlusPlusPortable/
  NotepadPlusPlusPortable.exe          # compiled Windows NativeAOT launcher
  App/
    AppInfo/
      appinfo.ini
      appicon.ico
      appicon_16.png
      appicon_32.png
    Notepad++/
      notepad++.exe                    # official upstream developer portable binary
      doLocalConf.xml                 # zero-byte portable configuration marker
      plugins/                        # official and user-installed plugins
      ...                             # original upstream release resources
  Data/
    Settings/                         # -settingsDir direct configuration and session
    PluginConfig/                     # backup of package-local plugin config, empty dirs too
    PluginsBackup/                    # backup of plugin files including customized binaries
    LegacyIniBackup/                  # older plugins' root INI files
    Recovery/Conflicts/               # non-destructive timestamp conflicts
    Recovery/launcher.log             # lifecycle/backup diagnostics
  Other/Source/
    PROVENANCE.json                   # upstream SHA, asset SHA, build revision, compiler SDK
    GPL-3.0.txt
    MIT-LAUNCHER.txt
    README.txt
```

## How portability works

- **Before startup**, the launcher derives the root from its own executable file, creates `Data/Settings`, verifies `doLocalConf.xml`, uses the *documented* `-settingsDir=...` argument, and always adds `-multiInst`. Thus the package does not join an already-running installed Notepad++ instance.
- The root `Data/Settings` profile is used directly, without copying users' installed `%APPDATA%\Notepad++` data. `config.xml`, `session.xml`, backup/session information, UDL and themes supported by `-settingsDir` are saved there by Notepad++.
- **Plugin settings** are different: the upstream portable plugin config directory can still reside in `App\Notepad++\plugins\config`. This is a **package-local** write path, not a host trace. Launcher startup/exit reconciles it with `Data/PluginConfig`. **Completely empty directories** are copied as directories, not dropped. The launcher also protects plugin binaries under `Data/PluginsBackup` because the shared installer replaces the `App` subtree.
- On next launch after an interrupted launcher/Windows crash, still-present plugin files inside `App` are reconciled back into `Data` before recovery. When files differ at equal timestamps, they are retained under `Data/Recovery/Conflicts` and not silently overwritten. A checksum is verified on each copied file. Junctions/symlinks are skipped rather than traversed.
- **Known limitation:** the launcher does not automatically overwrite a newly bundled upstream plugin DLL with an older user plugin backup; missing plugin files are restored, and the backup remains for manual comparison. This avoids undoing upstream security fixes. Files written by unvetted third-party plugins to arbitrary host paths are not blindly harvested.
- Default operation creates **no shortcuts, default-app registrations, COM registrations, HKLM/HKCU entries or autostart**. Shell/registry removal is deliberately **not implemented** without attributable runtime evidence. Windows can keep file-open history/Recent Items, Defender/SmartScreen and filesystem metadata; these are OS-owned traces.

**Do not install under Program Files.** Notepad++ documentation states its built-in local-config marker may be ignored in protected Program Files locations. Use a normally writable folder.

## Security and provenance

- Stable release tags/assets are official `notepad-plus-plus/notepad-plus-plus`. Source commit and exact official archive SHA-256 are recorded under `Other/Source/PROVENANCE.json`.
- Upstream `npp.<version>.checksums.sha256` must contain the selected asset's digest. Release notes (when published) and GitHub asset digest (when exposed) must not disagree. Untrusted mirror downloads, unsafe ZIP paths, and symlinks are rejected.
- The upstream Notepad++ code is GPL-3.0-or-later; the launcher source is MIT. Retained official developer archive components may have independent plugin notices, which remain in the archive. Do not claim this repackaging is endorsed by upstream or PortableApps.com.
- Publisher dry-run runs before publication, and `keep-releases=3`, `prune=false` by default. The shared publisher refuses overwrites when published assets differ. Publication uses only this builder's `GITHUB_TOKEN`, to this builder repository.
- For repeat builds, use the workflow `revision` input to choose a new builder/package revision if code/toolchain changes the binary even though the upstream version remains identical. The publishing action deliberately prevents silent replacement of existing release bytes.

## b1r2 fix: upstream nonempty local-configuration marker

The first real Windows GitHub Actions run compiled the x64 NativeAOT launcher and verified Notepad++'s archive checksum, but stopped in packaging because the upstream `doLocalConf.xml` was not zero bytes. The file is a zero-byte portable-mode **flag** per Notepad++'s documentation; it is not a configuration document requiring XML parsing. b1r2 saves the original bytes in `Other/Source/upstream-doLocalConf.xml.original`, records their size and SHA-256 in `PROVENANCE.json`, and makes only the staged file an empty marker. The official downloaded ZIP is never edited. Two regression tests cover missing, empty and nonempty cases. The b1r2 GitHub Actions log confirms marker normalization now succeeds, but the next directory creation step failed with WinError 183. GUI runtime acceptance is still pending.

## b1r3 fix: safe reuse of the Source staging directory

The b1r2 Windows run (`logs_115267011235(1).zip`, 2026-11-09) confirmed that the official archive marker normalization succeeded. The backup in `Other/Source` was already created by `normalize_portable_marker()`, but line 344 used `mkdir(parents=True)` without `exist_ok=True`, causing `FileExistsError: [WinError 183]`. b1r3 makes that directory creation idempotent (`mkdir(parents=True, exist_ok=True)`) **without deleting or overwriting the preserved upstream evidence**. No user Data or existing host paths are modified by this correction.

An added offline integration regression test runs the real source staging, provenance writing, ZIP generation, package validation and a repeat deterministic build using controlled dummy PE and icon *test fixtures*. This fixture test is not a claim that the actual Notepad++ binary or installer was run. The pinned installer and publisher remain at v1.0.0 and v1.1.1.

**Suggested GitHub Desktop commit summary:** `Fix Notepad++ PortableApps Source staging collision (b1r3)`.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `No numeric stable release found` | Check GitHub upstream API reachability and rate limits. API errors are not treated as missing releases. |
| `Official release contains nonempty doLocalConf.xml` | b1r1-only issue. Replace the builder kit with b1r3. It preserves the original marker and makes a valid empty marker inside staging. |
| `FileExistsError: [WinError 183]` for `Other\Source` | b1r2-only issue. Use b1r3: reuse the Source directory already created to protect the original portable marker. |
| `SHA256 MISMATCH` | Do not run the archive. The builder aborts and deletes the invalid download. Review official upstream release assets. |
| `NativeAOT launcher compilation failed` | Check `dotnet publish` logs in Actions. Ensure Windows 2022 hosted image provides C++ linker/SDK; the kit does not fall back to scripts or disguised EXEs. |
| `shared action tag commit unexpectedly changed` | The pinned tag is not the previously inspected revision. Stop, audit the new version and intentionally revise the kit. |
| `Failed to protect a portable file` | Close Notepad++, inspect `Data\Recovery\launcher.log`, free space/permissions/locked files. Files are preserved instead of being deleted. |
| Portable already running | Use the existing Notepad++ window's **File > Open**; the launcher blocks parallel use of a single profile. |
| Plugin missing after upgrade | Inspect `Data\PluginsBackup` and selectively restore a compatible plugin. Do not bulk overwrite new built-in DLLs. |
| Installer failed after ZIP passed | Get the workflow's `validated-notepadplusplus-zip-installer-failed` artifact, and inspect the shared NSIS error. Do not represent it as an installer success. |
| Data absent after installer extraction | The shared installer intentionally does not ship pre-existing `Data`; it creates it. Run the launcher to initialize settings. For ZIP, `Data` folders are already present. |
| Reinstall reports unfinished backup | Preserve and inspect `.__UPB_Backup` and `.__UPB_Stage`, restoring owned App/Other/launcher as instructed by the shared installer. Never delete Data. |

## Verification limits

Local offline tests validate scripts/YAML structure, numeric versions, checksum parsing and malicious ZIP traversal rejection. The Windows-hosted workflow is designed to compile and statically verify the launcher, real app and NSIS installer. It **does not prove interactive GUI startup, plugin migrations, external host-trace absence, notifications, real installer upgrades, or Windows crash recovery**; perform the manual acceptance checklist in `docs/ACCEPTANCE.md` and record your own observations. See `docs/AUDIT.md`, `docs/DATA-SAFETY.md` and `docs/STATUS.md`.
