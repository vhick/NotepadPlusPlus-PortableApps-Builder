# Implementation and verification evidence

**As authored:** 2026-11-09. This is a downloadable builder source ZIP. Not an executable application release and not a GitHub release.

| Item | Status at kit creation | What was actually done |
|---|---|---|
| Mode selection | SOURCE-INSPECTED | PORTABLEAPPS only, official Notepad++ portable ZIP selected |
| Latest release | SOURCE-INSPECTED | Public GitHub release v8.9.9 and asset/checksum names reviewed |
| Configuration and plugin locations | SOURCE-INSPECTED | Upstream manual, installer source and official community PortableApps launcher compared |
| Shared Package Builder interface | SOURCE-INSPECTED | v1.0.0 action.yml, build.ps1, common.ps1, NSIS script reviewed; commit-prefix guard implemented |
| Shared publisher interface | SOURCE-INSPECTED | v1.1.1 action.yml and publish.py reviewed; `dry-run` then optional publication |
| Stable version and SHA-256 resolver | STATIC-VALIDATED | Python unit tests for numeric versions and official checksum parsing passed; live API requests not run locally |
| Secure ZIP extraction | STATIC-VALIDATED | Synthetic malicious traversal ZIP rejected |
| Preservation of empty directories | STATIC-VALIDATED | Generated synthetic ZIP kept nested empty directory |
| Independent generated ZIP metadata | STATIC-VALIDATED | Synthetic ZIP content, CRC and repeated-output equality tested |
| Workflow syntax | STATIC-VALIDATED | Both workflows parsed as YAML in authoring environment; GitHub Actions runner not invoked |
| Launcher C# source | STATIC-VALIDATED | Program and csproj created; not compiled on Windows in authoring environment |
| Windows x64 NativeAOT executable | NOT YET VERIFIED | Compilation is a mandatory step when Actions runs |
| Real NPP portable archive download and checksum | NOT YET VERIFIED | Version-specific official SHA will be checked by the workflow when run |
| Real PortableApps ZIP | NOT YET VERIFIED | Produced only after actual launcher compile and official asset staging in CI |
| Package-local configuration runtime | NOT YET VERIFIED | Requires actual Notepad++ GUI launch on Windows |
| Plugin configuration backup/empty tree restoration | NOT YET VERIFIED | Implemented, but not Windows-compiled or runtime tested |
| Arbitrary third-party plugin behavior | NOT YET VERIFIED | Outside narrowly supported source paths; no blanket host scavenger |
| ShellGuard/external host traces | NOT YET VERIFIED | No evidence-based runtime-owned trace requiring removal confirmed; no destructive shell scavenger implemented |
| Notification and installed-app coexistence | NOT YET VERIFIED | Manual GUI and shell snapshot tests required |
| Shared custom NSIS installer generation | NOT YET VERIFIED | Only the shared action performs it on Windows CI |
| Actual NSIS installation/upgrade/rollback | NOT YET VERIFIED | User/Windows VM manual acceptance needed |
| Release publisher creation | NOT YET VERIFIED | Requires running workflow and choosing publish |
| User confirmed working | NOT YET VERIFIED | Awaiting user's Windows results |

**Compile status and release status must never be inferred from presence of this source ZIP.** GitHub Actions steps run on a future invocation, not during kit authoring. The recipe will fail rather than silently substitute CMD scripts for the compiled launcher. The packaging-only workflow is separately available for previously validated release ZIPs.

## Identified constraints

- The official `doLocalConf.xml` mode is not honored in protected Program Files locations; launcher also uses `-settingsDir` and expects a writable Data directory.
- Plugin managers or self-updaters can create temporary/host effects that require actual Windows observation. This kit does not claim to suppress those behaviors.
- The shared NSIS installer replaces the entire App/Other trees and keeps Data. This is why every successful launcher exit backs up the plugin tree. A user who runs the installer while a crashed launcher has unsaved App changes needs to back up App manually first.
- File associations, COM, HKLM and shell entries are not created or removed by this launcher. Optional user actions inside Notepad++ or third-party plugins remain outside the controlled contract.
- Windows launcher binaries built from source here are unsigned community executables; they are not Notepad++ upstream signatures or official PortableApps.com certified installers.
- An official detached signature is not validated without a verified, pinned upstream signing key. Official SHA-256 checksum-file verification is implemented and required.
- Build toolchain `8.0.x` patch version floats with hosted SDK image and is recorded in provenance; choose a new builder revision when SDK or builder code changes.

## November 9, 2026: b1r1 Windows failure and b1r2 remediation

- **WINDOWS-COMPILED:** b1r1 produced the actual NativeAOT launcher successfully (GitHub Actions Windows-2022 runner, step 5).
- **SOURCE/CHECKSUM:** b1r1 reached staged marker validation after downloading and checking the official archive digest (step 6).
- **FAILED/BLOCKED:** b1r1 rejected the nonempty `doLocalConf.xml` in the official archive.
- **STATIC-VALIDATED:** b1r2 preserves marker bytes and their SHA-256 for attribution, creates a zero-byte marker only in staging, and adds unit tests.
- **NOT YET VERIFIED:** b1r2 Windows Actions run, Notepad++ GUI portability, custom NSIS installer, and publication.
