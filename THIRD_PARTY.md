# Third-party software

MacKit does not bundle Neovim, Ghostty, Hammerspoon, tmux, Karabiner, yabai/skhd, Atuin or Homebrew binaries. Install these applications from their official distribution channels.

Neovim plugin repositories and pinned revisions are declared in components/nvim/lua/plugins and lazy-lock.json. Their original licenses apply to downloaded plugins. Plugin updates are explicit user operations.

Yazi plugins included in components/yazi/plugins retain their original notices and license files where provided. The tmux configuration is adapted from the user's configuration, with upstream inspiration acknowledged in its header (theniceboy/.config).

Hammerspoon modules originate in the author's MIT-licensed configuration repository. MacKit preserves that MIT notice under components/hammerspoon/LICENSE.

The WeChatUnrevoke website is a design/workflow reference. No AGPL implementation files from that project are bundled with MacKit.
# macOS App runtime

The macOS application includes CPython 3.12, distributed under the Python Software Foundation license. The full license is included as `Contents/Resources/Python-LICENSE.txt`. The runtime is packaged with PyInstaller, whose bootloader exception permits distribution of bundled applications under their own license. The application UI uses Apple system frameworks.

