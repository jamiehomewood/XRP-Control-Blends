# Installers for the Igloo / work PC

Copies of the official downloads, kept here in case the work network blocks them.

| File | What it is | Source |
|---|---|---|
| `OBS-Studio-32.2.2-Windows-x64-Installer.exe` | OBS Studio 32.2.2 | https://github.com/obsproject/obs-studio/releases |
| `OBS_Spout2_Plugin_Install_v1.12.0.exe` | Spout2 output plugin for OBS (needs OBS **32.1 or newer**) | https://github.com/Off-World-Live/obs-spout2-plugin/releases |
| `win-spout-1.12.0-windows-x64-portable.zip` | Same plugin, for a portable (zip) copy of OBS | as above |

## Order

1. Close OBS completely (end `obs64.exe` and any `obs-browser-page.exe` in Task Manager if it hangs).
2. Run the OBS installer (installs over the top, keeps scenes and settings).
3. Delete `C:\ProgramData\obs-studio\plugins\win-spout` if an earlier plugin install failed.
4. Run the Spout plugin installer.
5. Open OBS → **Tools → Spout Output Settings** → name `GlendaScene` → Start.

These files are large and only needed once: they can be deleted from the repo afterwards.
