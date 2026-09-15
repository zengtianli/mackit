# Configuration and recovery

MacKit links native component sources into the usual application locations. `mackit plan` shows every path before installation. `mackit status` includes installed profile and transaction receipts.

## Local files

| File under ~/.config/mackit | Purpose |
|---|---|
| local.zsh | private shell environment and workflows, loaded before final standard aliases and keymaps |
| keymaps.zsh | explicit final local shell key override |
| local.lua | final Neovim override after plugins and standard keymaps |
| hammerspoon.lua | Lua table of local Hammerspoon preferences and optional command paths |
| hotkey_overrides.json | Hammerspoon menu enabled states and special keyboard features |
| ghostty.conf | final Ghostty override |
| actions.json | named argv arrays for optional external document actions |
| paths.json | optional local OCR module path |
| karabiner-device-settings.json | local devices and machine_specific overrides merged during apply |

For example, `actions.json` may contain `{"format":["my-formatter","--write"]}`. Running `mackit action format -- "file with spaces.md"` preserves argument boundaries and invokes that command without shell expansion.

Do not put credentials in a public component. Your local files remain yours; MacKit neither uploads them nor places them in release archives.

## Recovery

Backups and transaction receipts live in `~/.local/state/mackit/`. `mackit restore` reverses the latest active transaction. It restores previous files or symlinks and preserves local additions.

If a managed link has been replaced, restore reports the path and refuses to overwrite the new content. Move or preserve the new content, then retry. Interrupted installs with an `installing` receipt can also be restored. Do not delete state while you still need its backups.

## Behavior changes in 0.1.0

- Neovim `sh` always splits left in tianli; substitute-to-word-end uses `se`.
- Completion owns insert-mode Ctrl-L; next Copilot suggestion uses Alt-L.
- Right Option → Hyper has one owner, Hammerspoon. The duplicate Karabiner remapping is removed.
- Yazi keeps `l` smart-enter; input Ctrl-U clears to beginning, Ctrl-K to end.
- tmux layout keys call its built-in layouts; no missing external layout script.
- Saving yabai configuration no longer restarts its service implicitly.
- Personal letter-coded line jumps are retained and generated from one concise declaration.

## Application behavior

Neovim plugins can load on file type or first use. Custom keyboard declarations stay centralized even when the implementation loads lazily. Plugin defaults are documented as plugin defaults rather than copied into MacKit's registry.

Ghostty additional files load after their parent in declared order. See [Ghostty's configuration reference](https://ghostty.org/docs/config). Your macOS Application Support Ghostty configuration can override XDG configuration; inspect both locations if a setting appears ineffective.


## Preset changes and generated files

Restore the current preset's active installation transactions before changing presets. This prevents a desktop keyboard component from staying active while its new profile hides it. Applying selected components within the same preset is additive; it does not uninstall previous components.

Karabiner is generated into the transaction directory because its GUI rewrites its JSON. Edit the canonical `components/karabiner/karabiner.json` and run `mackit apply --components karabiner` to regenerate. Preserve any intentional GUI edits before applying again. Ghostty uses generated include paths and a final optional local override.

The optional tmux TPM plugins require a separate TPM installation in `~/.tmux/plugins/tpm`; tmux itself works without them. Existing Zim installations are reused; a fresh shell falls back to native completion and the installed CLI tools.
