# Interactive Windows acceptance checklist (NOT YET VERIFIED)

Use a **disposable Windows 10/11 test account or VM**, with ProcMon/Registry comparison tools if possible. Keep a real installed Notepad++ profile containing test data, and a backup of that profile. Do not run these tests on production files. Record test date, build tag, commit, ZIP/installer SHA-256, observed paths and failures.

- [ ] Workflow builds genuine NativeAOT `NotepadPlusPlusPortable.exe` and official x64 `notepad++.exe`; signatures/architecture and SHA-256 proven.
- [ ] ZIP extracts and root launcher starts Notepad++ from `C:\PortableApps\NotepadPlusPlusPortable` (writable, no elevation).
- [ ] Check **? > Debug Info**: local config should be on; confirm `Data\Settings\config.xml`, `session.xml`, UDL, themes and backup/session path behavior.
- [ ] Change settings, create/close tabs, save a named session, exit fully, restart and verify persistence.
- [ ] Open a document with spaces and Unicode characters through root launcher arguments; inspect actual file loaded.
- [ ] Open an installed Notepad++ instance first, then start portable version; confirm both are separate and installed settings untouched.
- [ ] Try simultaneous launches from the same portable root. The second should be refused without destroying saved data.
- [ ] Create `App\Notepad++\plugins\config\nested\completely-empty-dir`; launch and close; verify it is also in `Data\PluginConfig`.
- [ ] Create a user plugin under App and test Plugins Admin; exit, verify `Data\PluginsBackup`, check plugin behavior after restart.
- [ ] Kill launcher and app from Task Manager during a controlled test; relaunch and verify reconciliation of plugin changes and no data loss.
- [ ] Test conflicting versions in App versus Data, equal-timestamp collisions, locked files, and junctions; verify file preservation and `Data\Recovery` diagnostics.
- [ ] Relocate the entire package (including Data) to a drive with a different letter/Unicode path; verify settings and sessions. Handle absolute document paths separately.
- [ ] Take Process Monitor/Regshot snapshots of `%APPDATA%`, `%LOCALAPPDATA%`, `%PROGRAMDATA%`, `%TEMP%`, HKCU/HKLM, Desktop, Start Menu and Jump Lists before/during/after. Attribute only exact app/plug-in paths, never delete unrelated data.
- [ ] Test PortableApps Platform menu discovery/refresh and launcher operation from its menu.
- [ ] Test installed-app coexistence, file associations, URL protocols, notifications and plugin GUI; compare Windows shell state during/after. Nothing should be silently registered by the builder.
- [ ] Close portable app; use custom NSIS `.paf.exe` to install and reinstall to target; check no other app is altered.
- [ ] Upgrade with modified plugin INI/config/DLL and nested empty directories, verify Data retention and rehydration. New core plugin DLLs must not be silently replaced by stale backup.
- [ ] Interrupt an upgrade in disposable VM; inspect shared `.__UPB_Backup` and recovery steps without deleting Data.
- [ ] Roll back using a full-folder snapshot; verify compatible config and plugin versions.
- [ ] Verify unsigned-launcher warning behavior, SmartScreen interactions, and upstream developer signatures if available. Do not disable antivirus.

**Status to report separately:** Source inspect, static scripts, Windows compiled, launcher functionality, configuration containment, plugin recovery, installed coexistence, shell/notification behavior, installer install/upgrade/rollback, publisher release, and user confirmation. A passing GitHub Actions job alone is not a substitute for this list.
