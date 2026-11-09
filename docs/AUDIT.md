# Notepad++ v8.9.9 PortableApps-only source and behavior audit

**Audit date:** 2026-11-09. **Stable upstream release:** `v8.9.9` (2026-11-06, GitHub release short SHA `41cd103`). The build resolves the full tag commit at runtime rather than hard-coding an abbreviated SHA.

**Sources consulted:**

- Official release page: https://github.com/notepad-plus-plus/notepad-plus-plus/releases/tag/v8.9.9
- Official user manual, configuration paths: https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/config-files.md
- Official user manual, documented command line: https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/command-prompt.md
- Source installer portable/profile logic: https://github.com/notepad-plus-plus/notepad-plus-plus/blob/master/PowerEditor/installer/nsisInclude/mainSectionFuncs.nsh
- GNU C++ build definitions: https://github.com/notepad-plus-plus/notepad-plus-plus/blob/master/PowerEditor/gcc/makefile
- Official PortableApps launcher comparison (not copied here): https://github.com/PortableApps/AppConfigs/blob/master/N/Notepad%2B%2B/Notepad%2B%2BPortable.ini
- Pinned Package Builder: https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/action.yml
- Pinned Package Builder NSIS installer implementation: https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/nsis/community-installer.nsi
- Pinned publisher: https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/action.yml

| Finding | Source evidence and status | File or registry path | Responsible component | NATIVE remedy (NOT selected) | PORTABLEAPPS remedy | Data safety | Functionality tradeoff | Test | Limitation |
|---|---|---|---|---|---|---|---|---|---|
| Local portable mode | **SOURCE-INSPECTED** user manual and NSIS source | `doLocalConf.xml` next to `notepad++.exe` | Notepad++ | Not applicable | Zero-byte marker required in packaged App | Never touch installed profile | None in writable folder | Check marker and UI Debug Info | Marker ignored in Program Files |
| Primary configuration | **SOURCE-INSPECTED** user manual and command line | `%APPDATA%\Notepad++` normally; package `Data\Settings` with `-settingsDir` | Notepad++ | Not applicable | Launcher passes documented command switch before startup | Direct in-place Data, no host profile move | No cloud profile redirection needed | Change config, session, relaunch | Third-party plugins may not honor it |
| Plugin settings | **SOURCE-INSPECTED** installer and plugin APIs | `App\Notepad++\plugins\config` in local portable mode | Notepad++ plugins | Not applicable | Package-local reconciliation with `Data\PluginConfig` | Copy verified, newer-host-external paths not touched, empty dirs retained | Single launcher active | Create empty plugin dir, restart, upgrade | Plugin-created arbitrary extra paths remain unproven |
| Custom plugin binaries | **SOURCE-INSPECTED** plugin layout and shared installer source | `App\Notepad++\plugins\<plugin>` | Notepad++ plugin manager/plugins | Not applicable | Preserve full plugin tree under `Data\PluginsBackup`; restore missing files only | Avoid old DLL overwriting new built-in versions | Updated bundled DLL may take priority | Install plugin, exit, shared installer upgrade, relaunch | Version compatibility must be checked manually |
| Legacy plugin .ini | **SOURCE-INSPECTED** official PortableApps launcher precedent | `App\Notepad++\*.ini` | Legacy plugin | Not applicable | Bounded root INI backup into `Data\LegacyIniBackup` | No wildcard host scanning | None expected | Create INI, restart, upgrade | Other legacy plugin paths not known |
| Self-update/Plugins Admin | **SOURCE-INSPECTED** manual, upstream files | GUP/plugins tree inside App; potential update installer host changes | Upstream updater | Not applicable | Preserve updater assets; advise builder-managed app upgrades | Never delete GUP or overwrite installed updater | Built-in updater remains enabled if user chooses | Test Plugins Admin interactively | Auto update must be assessed interactively |
| Installed app associations | **SOURCE-INSPECTED** Notepad++ installer; not runtime-proven | Optional HKCU/HKLM classes, Explorer context menu, user associations | Windows shell/installer | Not applicable | No default associations/registrations by launcher or shared installer | No registry deletion | Must opt in outside kit | Diff HKCU/HKLM and shortcuts | User-activated associations persist by design |
| Portable app single instance | **SOURCE-INSPECTED** `-multiInst` | Package-local running process | Notepad++ | Not applicable | `-multiInst`, package-specific mutex; block parallel launcher sessions | Avoid concurrent writes | Second launch cannot forward a document into first portable window | Launch with a file, repeat launch | GUI runtime not tested |
| Standard host caches | **INFERRED** Windows behavior, not a Notepad++ user profile | Recent Items, Prefetch, security logs, shell history | Windows | Not applicable | No broad cleanup (not app-owned) | Host protected | Windows traces may persist | ProcMon before/after | Cannot guarantee zero Windows activity |
| PortableApps installer replacement | **SOURCE-INSPECTED** shared NSIS source | `App`, `Other`, launcher replaced; `Data` preserved | Shared Package Builder | Not applicable | Mirror plugin modifications to Data before upgrade | Backup/rescue by shared NSIS | Requires app closed; no in-use upgrade | Manual install/upgrade/rollback | Not yet run on interactive Windows |

**Licensing/build:** Notepad++ is C++ (Scintilla and Lexilla, Win32, GNU C++/Visual Studio toolchains) with GPL-3.0-or-later application licensing. The selected binary source is the officially published x64 portable ZIP, so application recompilation is not appropriate to this selected PORTABLEAPPS mode. This kit compiles its *own root launcher* from readable C# using .NET 8 NativeAOT; no source patches are needed for Notepad++ because `doLocalConf.xml` and `-settingsDir` are upstream-supported.

**Evidence distinction:** Public source/manual/release inspection occurred; no interactive local Windows application, installer, plugin manager or shell/notification test occurred during kit authorship. The workflow will fetch the exact source-commit identity and official signed/checksum assets independently when run. Code signing for the unsigned community launcher is not claimed.

**Not implemented (evidence absent):** broad `%APPDATA%`, `%LOCALAPPDATA%`, `%PROGRAMDATA%`, `%TEMP%`, Desktop, Start Menu, HKCU/HKLM or COM scavenging; service/drivers/autostart; cross-process injection; profile sharing; guaranteed portable storage for arbitrary third-party plugins. Every one would require separately observed attribution and owner verification. The selected mode is *not* NATIVE.

### b1r2 compatibility finding

The b1r1 Windows Actions run on 2026-11-09 found a nonempty `doLocalConf.xml` in the checksum-verified official ZIP and rejected it. This marker is documented upstream as an empty portable-mode flag. b1r2 preserves the original file under `Other/Source` and normalizes only the staged package marker. Actual Windows runtime acceptance is pending.

### b1r3 packaging-state finding

**LOG-OBSERVED (2026-11-09):** The b1r2 action run failed at `scripts/npp_build.py:344`, after `normalize_portable_marker` had successfully created `Other/Source` and backed up the original 308-byte upstream `doLocalConf.xml`. Recreating that folder without `exist_ok=True` fails on Windows with `FileExistsError [WinError 183]`. The b1r3 change is confined to idempotent creation of the package's `Other/Source` directory; application runtime behavior and the pinned shared actions are unchanged. An offline fixture reproduces the normal marker → backup → staging → package sequence to prevent recurrence.
