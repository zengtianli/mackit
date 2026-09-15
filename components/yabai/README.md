# yabai / skhd

Optional window manager and hotkey daemon. Install with `mackit apply --components yabai` after installing the applications and granting their required permissions.

- `config/yabairc`: window management behavior. The current preset uses float layout.
- `config/skhd/skhdrc`: all skhd hotkey declarations.
- `scripts/`: actions called by the declarations; `config/scripts` links to this directory.

MacKit does not start, stop, or enable these background services during installation. Manage their lifecycle using the installed applications’ documented commands. The Hammerspoon preset also provides explicit window management actions.

Query keys with `mackit keys --component yabai`; edit settings with `mackit edit yabai`.
