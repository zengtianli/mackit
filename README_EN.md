# Tianli MacKit

[中文](README.md) · [Website](https://mackit.tianli.cyou) · [Shortcut handbook](https://mackit.tianli.cyou/keys.html)

A Mac configuration kit with one place to find your keys, edit native configuration, and restore what you had before.

MacKit brings zsh, Neovim, Hammerspoon, Ghostty, tmux, Yazi, Karabiner and yabai/skhd into one maintained source. A native SwiftUI app and the standard-library CLI share the same installation engine. The app bundles its runtime and does not stay resident when closed. Existing applications keep their own runtimes.

## Download the macOS app

[MacKit 0.2.0 for Apple Silicon (DMG)](https://github.com/zengtianli/mackit/releases/download/v0.2.0/MacKit-0.2.0-arm64.dmg) · [Website and demo](https://mackit.tianli.cyou/)

Requires macOS 14+ and Apple Silicon. The app includes its runtime: Python and Git are not prerequisites to launch it. Developer ID signed and notarized by Apple.

1. Open the DMG and drag **Tianli MacKit** to **Applications**.
2. Select a preset and components in **安装配置**, then click **预览配置变化** to review changes.
3. Use **安装缺失软件与依赖** to install missing tools. If Homebrew is missing, use **安装 Homebrew** and complete its system installer.
4. Choose **备份并安装配置**, then reopen your terminal and the selected applications.

The Chinese-language app includes shortcut search, configuration editing with backups, dependency checks, and restoration. Existing MacKit sources are reused; fresh installations use `~/.local/share/mackit`. Enter administrator passwords only in the system installer. Accessibility/Input Monitoring permissions remain user-controlled. Optional yabai/skhd installation and services are not automated.

Keyboard navigation: ⌘1–4 switch pages, ⌘F search, ⌘R refresh, ⌘S save, ⌘Return preview. The app package is arm64; Intel users can use the CLI below.

[App guide](docs/macos-app.md) · [Build the app](docs/build-app.md)

## CLI installation

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
mackit doctor                       # sources, dependencies, declared key conflicts
mackit restore                      # restore the most recent installation
```

Choose components: `./install.sh --apply --components zsh,nvim,tmux`. Existing files and symlinks are moved into a transaction backup, not discarded. If you replace an installed link with new content, restore refuses to erase that content. Local additions in `~/.config/mackit/` survive updates and restores.

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
python3 scripts/package.py
```

Tests cover installation into isolated homes, idempotence, rollback, preservation of new user files and real headless Neovim numbering. Source checks do not prove which external application receives a physical key, nor do they verify macOS permissions. See [validation](docs/validation.md) for the release's tested scope.

MIT for MacKit's original code. Bundled third-party components retain their licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).
