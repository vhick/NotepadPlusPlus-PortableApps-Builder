# Data safety, upgrades, crash recovery and host coexistence

## Always keep Data

`Data/Settings` is the authoritative Notepad++ profile, while `Data/PluginConfig`, `Data/PluginsBackup` and `Data/LegacyIniBackup` are backup copies for package-local plugin files. `Data/Recovery/Conflicts` preserves timestamp collisions and `Data/Recovery/launcher.log` records errors. Never remove Data during installs/upgrades. Do not use the installer with Notepad++ open.

## Supported recovery lifecycle

1. On start, assert actual Notepad++ executable exists and `doLocalConf.xml` is present. Do not silently drop into installed-profile mode.
2. Reconcile surviving package-local plugin config into Data before restoring anything from Data. This protects data even if Windows killed the launcher during the previous session.
3. Reconcile Data back into the fresh App after upgrades. Plugin binary files are restored *only if absent*, preventing stale DLLs from silently replacing new upstream DLLs.
4. Set `-settingsDir` to the directly writable Data path before Notepad++ initialization and run with `-multiInst` for installed-app isolation.
5. Wait for full portable-app exit, and back up modified plugin folders/legacy INIs. The launcher neither kills processes nor removes host files or registry keys.
6. Copy checksums are verified before committing file replacement, and overwritten copies are saved as conflicts. Link/junction recursion is skipped. Failures are logged and surfaced, not silently concealed.

**Important limitation:** the launcher is not a transactional filesystem, database checkpoint system, or resident monitor. It has no rollback for arbitrary plugin writes. If the portable root itself is deleted while the app is running, no launcher can recover data that was never persisted. For maximum safety, copy the entire package directory (including App and Data) before every upgrade.

## Shared installer guarantees and limits

The inspected pinned `custom-nsis` installer source stages a new `App`, `Other`, and root launcher, makes a backup of the previous managed files, moves staged files into place and preserves Data. It rejects mismatched AppID, an existing interrupted `. __UPB` transaction and running app binaries. It cannot rescue plugin files modified since the *last successful launcher shutdown* if the previous launcher has been killed and the user runs the installer anyway. Thus **launch then normally exit the current portable Notepad++ before any upgrade**; if not possible, back up the entire old `App/Notepad++/plugins` folder yourself.

## Installed Notepad++ and Windows

The launcher has its own mutex specific to the portable root and gives Notepad++ `-multiInst`. The latter is needed because upstream Notepad++ may otherwise forward an invocation to another existing instance, possibly installed. The launcher does not alter `%APPDATA%`, `%LOCALAPPDATA%`, `%USERPROFILE%`, `%TEMP%`, registry, file associations, Explorer context menu or shortcuts. Other applications, enabled integrations, Windows-managed caches and third-party plugins remain outside its control.

## Relocation

Exit Notepad++ then move the full `NotepadPlusPlusPortable` folder to another disk, account, or folder, keeping App and Data together. The launcher computes a new portable root from its EXE each time. **Warning:** `session.xml`, some plugin configs and document paths may preserve absolute drive letters. Do not blind-replace all XML strings; only update known file-path fields with backups. Test all opened documents and plugin configs after relocation.

## Rollback

Use an independent full-folder backup made before upgrading. Close the current package, back up any recent user files to a separate safe location, and restore both older `App`/launcher **and matching compatible older Data**. Keeping newer Data with older binaries can fail if XML or plugin schemas changed. Nothing in this kit deletes backups automatically.
