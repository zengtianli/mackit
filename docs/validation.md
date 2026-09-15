# Validation

Development environment: macOS on Apple Silicon. Tests use isolated HOME directories, real zsh and headless Neovim, and Lua syntax checks. No test synthesizes input on the user's desktop.

The current automated suite covers: reversible installation, repeat installation, mid-install failure rollback, refusal to overwrite newly created user files on restore, refusal of escaping parent symlinks, shell startup without the original user's Zim installation, argument boundaries for optional actions, native Lua syntax, and real visual-selection numbering through Space n l.

Physical desktop shortcuts, Accessibility/Input Monitoring permission and device-specific behavior need the selected applications and permissions. The CLI's doctor is a managed-configuration check, not an event-tap shortcut detective.

Version 0.1.0 evidence: 12 automated tests pass; the Hammerspoon menu/preset test runs with stubbed APIs and never invokes actions. Real local zsh, Neovim, Ghostty config validation and an isolated tmux server passed. The existing Mac switched to the Tianli preset with 19 managed links and an empty doctor issue list.

The 36-second tutorial replays real PTY output from a standalone archive in an isolated HOME. Extra reading holds are explicit; it is not realtime desktop video. The final command independently verifies the original shell file was restored. See `site/media/manifest.json` and `scripts/record-demo.py`.

Fresh plugin downloads depend on GitHub connectivity. This development network returned proxy 503 errors during a fresh install; the offline/native editing path and startup against an existing plugin cache were verified. Do not treat those checks as a guarantee that every optional plugin service works without its dependencies or account setup.

