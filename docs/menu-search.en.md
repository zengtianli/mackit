# Current-App menu search

MacKit provides an on-demand native menu-search panel without Raycast, Hammerspoon or cloud services. No daemon is added: the panel exits when closed. It captures the application owning the menu bar before showing the panel and reads fresh menu commands on each invocation.

Configure a trigger under MacKit's Window → skhd shortcuts: record a key, choose the MacKit menu-search action, then save and apply. This reuses the existing shortcut recorder and conflict checks. No new global shortcut is registered by default. You can re-record or remove the binding there.

The empty search lists all accessible menu commands. Type to filter command names and full menu paths, including Chinese and discontinuous token queries. Arrow keys select, Return executes, Escape or clicking another window cancels. Return during IME composition confirms the candidate instead. Standard text-editing keys are preserved. Disabled items are visible and cannot execute.

MacKit requires macOS Accessibility permission. Missing permission produces an explanation and a System Settings link; permissions are never changed automatically. Before execution, MacKit checks the actual menu element's owner, title and enabled state. A partial or timed-out scan is explicitly reported.

The shared native implementation is available through `mackit menu status --json`, `mackit menu show`, `mackit menu scan [--pid N] --json`, and `mackit menu execute --pid N --path-json '["View","Show Status Bar"]' --json`. Execution requires a unique full path and the target App to remain frontmost. All these commands reject an isolated `--home` rather than accessing applications outside that sandbox.

`MacKit --menu-self-test --output DIR` exercises the actual panel offscreen with fixture inputs and no external actions. Adding `--pid N` renders that application's real menu data. This verifies filtering and internal keyboard handling, but physical-hotkey invocation and external-App execution still require Computer Use while the user yields the computer.

The code was independently written with reference to [Raycast's manual](https://manual.raycast.com/navigation) and the [third-party extension](https://github.com/BalliAsghar/menu-bar-search-raycast). No source from Raycast's installed bundle or that repository was copied.
