# MacKit · 配置助手

“Configuration and Updates…” offers optional iCloud sync and configuration export/import for your preset and component selection. Portable choices live in `~/.config/mackit/portable-preferences.json`; installation receipts, source paths, permissions, private overrides and service state stay local. On a new Mac, restored choices can be previewed before the existing install workflow. “Check for Updates…” checks the official MacKit release on demand.

[中文](README.md) · [Website](https://mackit.tianli.cyou) · [Shortcut handbook](https://mackit.tianli.cyou/keys.html)

A Mac configuration kit with one place to find your keys, edit native configuration, and restore what you had before.

MacKit brings zsh, Neovim, Hammerspoon, Ghostty, tmux, Yazi, Karabiner and yabai/skhd into one maintained source. A native SwiftUI app and the standard-library CLI share the same installation engine. The app bundles its runtime and does not stay resident when closed. Existing applications keep their own runtimes.

Version 0.3.5 renames the app to **MacKit** (display name MacKit · 配置助手) and gives every app page a matching command (`status`, `prepare`, `plan`/`apply`, `deps`, `keys`, `file`, `window`, `restore`, `link`) for agents and scripts (see [Command line for agents and scripts](#command-line-for-agents-and-scripts)). Configuration content, shortcuts and install semantics are unchanged; upgrading from an older version is described below.

## Download the macOS app

[MacKit 0.3.6 for Apple Silicon (DMG)](https://github.com/zengtianli/mackit/releases/download/v0.3.6/MacKit-0.3.6-arm64.dmg) · [Website and demo](https://mackit.tianli.cyou/)

Requires macOS 14+ and Apple Silicon. The app includes its runtime: Python and Git are not prerequisites to launch it. Developer ID signed and notarized by Apple.

The local acceptance build is 0.3.6 (636); the public download remains 0.3.6 (0.3.6). Download size below refers to the public DMG, while runtime metrics identify the measured build.

<!-- lightweight:start -->
## Resource use

| Download | Idle memory | Idle CPU | Cold launch to window |
|---|---|---|---|
| **11.9 MB** (installed 23.9 MB) | **49.3 MB** | **0%** | **395 ms** |

Native SwiftUI; the configuration engine runs only for an action and exits, with no polling or scheduled tasks. Bundles a Python standard-library runtime with stripped symbols and no development-only files.

<sub>v0.3.5 (0.3.5) · Mac16,12 / Apple M4 / macOS 27.2 · Real local configuration: 14 components and 1,017 shortcut declarations, including existing external keymaps · measured 2026-10-01. Measured on the listed device; re-measured for each version. Memory uses phys_footprint; CPU is CPU time ÷ wall time over a 60-second sampling window; sizes in decimal MB. Raw data: [perf/lightweight.json](perf/lightweight.json).</sub>
<!-- lightweight:end -->

1. Open the DMG and drag **MacKit** to **Applications**.
2. Select a preset and components in **安装配置**, then click **预览配置变化** to review changes.
3. Use **安装缺失软件与依赖** to install missing tools. If Homebrew is missing, use **安装 Homebrew** and complete its system installer.
4. Choose **备份并安装配置**, then reopen your terminal and the selected applications.

The Chinese-language app includes shortcut search, configuration editing with backups, dependency checks, and restoration. The Windows page (⌘5) turns yabai settings into an explained form, records skhd shortcuts by pressing them and flags clashes with other tools, adds app rules visually, and regenerates yabairc / skhdrc with backups, optionally applying them to running yabai/skhd. Existing MacKit sources are reused; fresh installations use `~/.local/share/mackit`. Enter administrator passwords only in the system installer. Accessibility/Input Monitoring permissions remain user-controlled. Install yabai/skhd from their official instructions; once installed, the Windows page can start or stop them.

From 0.3.3 the `mackit` command ships inside the app: after installing from the app, `~/.local/bin/mackit` points into the app bundle and updates with it, while still working on the configuration source recorded at install (`edit`, `keys`, `doctor`, `update` are unchanged). Existing installs switch by installing again from the app, or by running `"/Applications/MacKit.app/Contents/Resources/core/bin/mackit" link`; `mackit restore <transaction>` brings back the previous link. Source checkouts installed with `./install.sh` keep their existing link.

The app is now named **MacKit** (display name MacKit · 配置助手, bundle ID `cyou.tianli.mackit` unchanged); 0.3.4 and earlier installed as Tianli MacKit. When upgrading, drag the new app to Applications, run `"/Applications/MacKit.app/Contents/Resources/core/bin/mackit" link` once, then move the old Tianli MacKit to the Trash; `mackit doctor` points out a link that still targets the old app.

Keyboard navigation: ⌘1–5 switch pages, ⌘F search, ⌘R refresh, ⌘S save, ⌘Return preview. The app package is arm64; Intel users can use the CLI below.

[App guide](docs/macos-app.md) · [Build the app](docs/build-app.md)

## CLI installation from source

Requires macOS, Python 3.11+, Git and the applications you choose. Neovim configuration requires 0.11+. Use Homebrew to install missing tools; `mackit deps` prints the selected dependency commands.

```sh
git clone https://github.com/zengtianli/mackit.git ~/.local/share/mackit
cd ~/.local/share/mackit
./bin/mackit deps
./install.sh                         # inspect changes
./install.sh --apply                 # back up and install
```

Start a new terminal, then:

```sh
config nvim                         # editor entry
mackit edit nvim-keys                # all custom editor keys
mackit keys 编号                     # find the 01_, 02_ numbering action
mackit doctor                       # sources, dependencies, key conflicts (incl. keys.d apps, Keyboard Maestro)
mackit restore                      # restore the most recent installation
```

Apps can register their shortcuts in `~/.config/mackit/keys.d/<app>.json` (`[{"component","mode":"global|app:<Name>","key","description"}]`). `mackit keys` lists them, and `mackit doctor` reports two tools claiming one global key, or an in-app key that a global key intercepts first. Active Keyboard Maestro hot-key macros are read in read-only.

Choose components: `./install.sh --apply --components zsh,nvim,tmux`. Existing files and symlinks are moved into a transaction backup, not discarded. If you replace an installed link with new content, restore refuses to erase that content. Local additions in `~/.config/mackit/` survive updates and restores.

## Command line for agents and scripts

Everything you can see or do in the app has a command (the GUI is for people, the CLI for agents). Both call one engine: `mackit/cli.py` owns planning, installing and restoring, and `mackit/gui.py` with `mackit/window.py` is the business layer behind each app page. Commands reuse the same validation, digest locks, backups and transaction records rather than a second implementation. Read commands take `--json` for a stable object with `"ok"` and never write state; failures exit non-zero, and with `--json` print `{"ok": false, "error": …}`.

```sh
mackit status --json                          # preset, source, app/source versions, transactions, mackit link state
mackit prepare --json                         # what the app's Preview does: prepare the configuration source (no-op when ready); needed before file and window writes
mackit plan --json                            # preview with a token
mackit apply --token <token>                  # install only if the targets are unchanged since the preview; one restorable transaction (a stale token creates nothing)
mackit doctor --json                          # sources, dependencies, command link, key conflicts; exit 1 on issues
mackit deps --json                            # installed state per formula/cask; --check exits 1 when something is missing
mackit deps --install                         # brew install only what is missing (real HOME only; progress on stderr, poll deps --json)
mackit keys 编号 --json                       # shortcut catalog as {ok, count, rows} (with keys.d and Keyboard Maestro)
mackit keys --conflicts-with ctrl+alt+h --json   # global-key clash hint, the same rule as the Windows page and doctor
mackit file list --json                       # every Files-page entry, including local / local-keys / hs-local
mackit file read nvim-keys --json             # content + sha256 digest
mackit file write nvim-keys --digest <digest> --from new.lua   # refused on a stale digest; the old file goes to editor-backups
mackit window status --json                   # yabai/skhd state, live values, saved settings/rules/hotkeys, actions, digest
mackit window set window_gap=8 layout=bsp     # validated, yabairc regenerated after a backup; --apply also updates running yabai/skhd
mackit window hotkey add --key ctrl+alt+h --action focus-west   # or --command '<one line>'; --replace for a bound key
mackit window hotkey remove --key ctrl+alt+h
mackit window rule add --app "System Settings" --manage off
mackit window save --digest <digest> --from window.json         # replace everything, same shape as window status --json's window
mackit window service stop skhd               # start/stop yabai or skhd (real HOME only)
mackit restore <transaction> --json           # undo the newest transaction
mackit link                                   # point ~/.local/bin/mackit at this app's command (recorded, restorable)
```

`--home <dir>` (any folder other than your own home) is a sandbox: no software installs, no service start/stop, nothing applied to running yabai/skhd, and no file written outside the folder. Whether you run the app's command or a source checkout's `bin/mackit`, the configuration source is prepared as the app prepares it, in `<dir>/.local/share/mackit`: `plan` reports it without creating it, and `prepare` or `apply` creates it from the built-in copy, so window and file writes land inside the sandbox. If a sandbox recorded a source outside itself (source commands before 0.3.5 did), that source is read-only there and writes are refused; start from a new folder.

Without `--home`, commands act on this Mac's real configuration, whose source is the folder recorded at install time. For an install from a git checkout (`./install.sh`) that is the checkout itself, so `mackit window …` and `mackit file write` change files in the checkout, just as saving in the app does.

Since 0.3.5 `keys --json` prints `{ok, count, rows}`; earlier versions printed a bare array of rows.

GUI-only: recording a key by pressing it (the CLI takes the key name), Reveal in Finder, opening the permission panes in System Settings, downloading the official Homebrew package and opening the system installer (`deps --json` gives the package URL when brew is missing), page switching and search focus, unsaved-draft and quit prompts, and the online handbook/GitHub links. The app reaches the same engine through `mackit gui`, an unlisted JSON channel.

## Profiles

- **developer**: native Neovim movement and Ctrl-W window commands; optional desktop integrations are not installed by default.
- **tianli**: S/Q save/quit, J/K move 15 lines, Space leader, Option-S tmux prefix and right-side modifier conventions. Select with `--profile tianli`. Business commands, credentials, history, Git identity and device identifiers are excluded from the release.

Hammerspoon starts with global shortcuts disabled in the developer profile. Enable individual shortcuts and keyboard rules through its menu bar. Installing configuration does not grant Accessibility/Input Monitoring permission or start background services.

## Where to edit

| Task | Command | Source |
|---|---|---|
| Neovim keys | `mackit edit nvim-keys` | `components/nvim/lua/config/keymaps.lua` |
| Line numbers | `mackit edit number` | `components/nvim/lua/config/options.lua` |
| zsh keys | `mackit edit zsh-keys` | `components/zsh/keymaps.zsh` |
| Desktop keys | `mackit edit hs-keys` | `components/hammerspoon/keymaps.lua` |
| tmux keys | `mackit edit tmux-keys` | `components/tmux/keymaps.conf` |
| Personal shell | `mackit edit local` | `~/.config/mackit/local.zsh` |

Key declarations and action implementations are separate. Plugin activation can still be lazy; the declaration stays in the keymaps owner. The handbook is generated from these native sources using `python3 scripts/build-handbook.py`.

## Local additions and updates

See [configuration and recovery](docs/configuration.md). Local hooks are opt-in and run only when explicitly invoked. Optional document tools and office automation are not bundled.

For a Git checkout, `mackit update` accepts only a clean working tree and a fast-forward update. Keep your edits in Git or local overlays; review `mackit plan` and apply after an update. Archive users can install a new release beside the previous release and apply from it.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build-handbook.py
bash scripts/build-app.sh --local     # development app build; installs and publishes nothing
```

Tests cover installation into isolated homes, idempotence, rollback, preservation of new user files and real headless Neovim numbering. Source checks do not prove which external application receives a physical key, nor do they verify macOS permissions. See [validation](docs/validation.md) for the release's tested scope.

MIT for MacKit's original code. Bundled third-party components retain their licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).
