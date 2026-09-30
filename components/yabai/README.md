# yabai / skhd

Optional window manager and hotkey daemon. Install with `mackit apply --components yabai` after installing the applications and granting their required permissions.

- `config/settings.json`: yabai settings and app rules. MacKit generates `config/yabairc` from it.
- `config/skhd/hotkeys.json`: skhd bindings (a catalog action or a one-line command per key). MacKit generates `config/skhd/skhdrc` from it.
- `scripts/`: actions called by the bindings; `config/scripts` links to this directory.

Change them in the MacKit app's 窗口 (Windows) page or with `mackit window`: `status`, `set KEY=VALUE`, `hotkey add|remove`, `rule add|remove` and `save`. Both validate the values, back up the previous files and rewrite `yabairc` and `skhdrc` together, so edit the JSON sources, not the generated files; hand edits to `yabairc` or `skhdrc` are overwritten on the next save.

Installing the component never starts, stops or enables these background services. Start or stop them explicitly with the 窗口 page or `mackit window service start|stop yabai|skhd`, or with the tools' own documented commands. `mackit window … --apply` also pushes saved settings to a running yabai and reloads skhd. The Hammerspoon preset also provides explicit window management actions.

Query keys with `mackit keys --component yabai`; check a new binding with `mackit keys --conflicts-with ctrl+alt+h`.
