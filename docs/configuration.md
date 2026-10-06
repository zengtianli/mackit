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

`hammerspoon.lua` returns a table whose keys override the portable defaults. Optional system behavior stays off unless enabled there: `return {ac_awake=true}` keeps the Mac awake while it is on AC power (`sudo -n pmset -a disablesleep 1`, restored to `0` on battery; a manual change holds until the next plug or unplug). It needs a passwordless sudo rule for `/usr/bin/pmset`; without one Hammerspoon logs the failure and sleep settings stay unchanged.

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

## Keyboard ownership after 0.3.6

- Two tools share the keyboard, split by what a key produces (2026-10-06). Karabiner maps keys to keys: layers, modifiers, tap-or-hold, per-app remaps. skhd runs programs: every key that starts a script or an app is an skhd binding in `components/yabai/config/skhd/hotkeys.json`. The Karabiner file holds no `shell_command`, and `tests/test_native.py` fails if one comes back. Nothing goes through Hammerspoon, so the keys work with Hammerspoon closed.
- The action keys call the scripts in `components/yabai/scripts/actions/` (Finder folder → `open -a Ghostty`, Music through `osascript`, the yabai service, mouse-follows-focus, the code-fence paste). A personal script is reached through `actions/local.sh <name>`, which runs `~/.config/mackit/bin/<name>` when that file exists and does nothing otherwise. The preset uses three such names: `lid-sleep`, `brew-maintain`, `smart-push`. Keep machine paths out of the public files and put them in those scripts.
- The actions left Karabiner because it keeps a single process slot for `shell_command` (the next command kills one that is still running) and gives it the default system `PATH` only. skhd starts each command on its own with the `PATH` its service was installed with.
- Moving a key to skhd changes three things. macOS asks once per target app whether skhd may control it (Finder, Music, System Events); a refusal is undone in System Settings › Privacy & Security › Automation. skhd does not see keys while Secure Input is on, for example with the cursor in a password field. The Finder terminal key is bound for every app and its script returns at once unless Finder is frontmost, so that chord no longer reaches other apps.
- Every action script reports with a macOS notification (`display notification`), so the feedback looks the same everywhere. Notifications stay silent while a Focus mode hides them. Hyper+P is a plain mapping to the system play/pause key and shows none: a notification would need a program.
- ⇧⌘V wraps the clipboard in a Markdown code fence and pastes it. `actions/code-fence-paste.sh` does it in order: read with `pbpaste`, write the fenced text with `pbcopy`, wait until every modifier is released, send ⌘V through System Events, notify, put the original text back a second later. The wait is needed because skhd fires while Shift and Command are still down; a ⌘V sent then arrives as ⇧⌘V and lands on the same binding. If the modifiers stay down for three seconds, or skhd lacks the Accessibility or Automation permission, the fenced text stays on the clipboard and the notification says so. Only plain text survives the round trip; an empty or non-text clipboard is left alone.
- `components/hammerspoon/keymaps.lua` still declares the earlier actions so that restoring the previous generation (`mackit restore`) keeps working. Nothing calls it now, and the Hammerspoon menu switches no longer affect any key.
- A running Karabiner does not always notice a new generation. After `apply`, rename each recent `~/.local/state/mackit/generations/*/karabiner` directory and rename it back until `/var/log/karabiner/core_service.log` shows `core_configuration is updated`; it watches the directory it last loaded from, which is not always the one before the newest.
- Right Option → Hyper (⇧⌘⌃), Ctrl+HJKL arrows outside terminals, ⌘H / ⌥⌘H / ⌃⌘H deletion, Safari ⇧⌘C and the system play/pause key are plain Karabiner mappings. This replaces the 0.1.0 note above that named Hammerspoon as the owner of Right Option.
- A single tap of either Shift switches between ABC and the system Simplified Pinyin. Shift held with another key or a click stays Shift: the rule passes Shift through at once (no `lazy`), because a lazy modifier never reaches a click from a trackpad or mouse that Karabiner does not grab. Pinyin → ABC uses `select_input_source`. ABC → Pinyin sends Control-Space, since Karabiner documents `select_input_source` as unreliable for input modes such as Pinyin. That direction needs the macOS shortcut "Select the previous input source" left on Control-Space and only these two input sources enabled.
- `tests/test_native.py` checks that Karabiner runs no command, that each action key is bound once in `hotkeys.json` to an executable script, and that Hammerspoon creates no hotkey or event tap.

## Application behavior

Neovim plugins can load on file type or first use. Custom keyboard declarations stay centralized even when the implementation loads lazily. Plugin defaults are documented as plugin defaults rather than copied into MacKit's registry.

Ghostty additional files load after their parent in declared order. See [Ghostty's configuration reference](https://ghostty.org/docs/config). Your macOS Application Support Ghostty configuration can override XDG configuration; inspect both locations if a setting appears ineffective.


## Preset changes and generated files

Restore the current preset's active installation transactions before changing presets. This prevents a desktop keyboard component from staying active while its new profile hides it. Applying selected components within the same preset is additive; it does not uninstall previous components.

Karabiner is generated into the transaction directory because its GUI rewrites its JSON. Edit the canonical `components/karabiner/karabiner.json` and run `mackit apply --components karabiner` to regenerate. Preserve any intentional GUI edits before applying again. Ghostty uses generated include paths and a final optional local override.

Karabiner keeps watching the directory it loaded from, and `apply` only repoints `~/.config/karabiner` at a new generation. To make a running Karabiner read the new file without restarting it, rename the previous generation's `karabiner` directory and rename it back (`mv "$OLD" "$OLD.nudge" && mv "$OLD.nudge" "$OLD"`, where `OLD` is what `readlink ~/.config/karabiner` printed before the apply). Then check `/var/log/karabiner/core_service.log` for a new `core_configuration is updated.` line. Run the apply on every Mac that shares the source: the generated file is per machine. Every reload also starts Karabiner's menu bar item and notification window again if they were closed, because the file sets neither `global.show_in_menu_bar` nor `global.enable_notification_window` and both default to on.

The optional tmux TPM plugins require a separate TPM installation in `~/.tmux/plugins/tpm`; tmux itself works without them. Existing Zim installations are reused; a fresh shell falls back to native completion and the installed CLI tools.
