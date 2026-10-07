import AppKit
import SwiftUI

// MacKit's side of the shared「配置与更新…」layer (AppLifecycle*.swift are byte copies of swift-shared). This file is the
// one place that names the product, its release channel and its portable settings. The window (MacKitApp.init) and
// the commands `mackit config …` / `mackit update check` / `mackit update install` are both built from it, so they
// read and write one thing and upgrade through one installer.
// The command line is the Python engine: it forwards those words to this executable (mackit/cli.py lifecycle_command),
// which answers in `command(_:)` before any NSApplication exists.
enum Lifecycle {
    static let name = "MacKit · 配置助手"
    static let command = "mackit"
    static let productID = "cyou.tianli.mackit"
    static let probeFlag = "--lifecycle-follow-probe"
    static let suiteVariable = "MACKIT_LIFECYCLE_SUITE"
    static let suitePrefix = "test.tianli.mackit."

    /// An isolated run (tests/test_lifecycle_cli.py): with APP_LIFECYCLE_SUPPORT_DIR the shared layer keeps its backups,
    /// sync record and "cloud" copy in temporary folders. MacKit's own two places then have to be temporary too.
    static var isolated: Bool { ProcessInfo.processInfo.environment["APP_LIFECYCLE_SUPPORT_DIR"] != nil }
    /// The one release channel: the window's「检查更新」and `mackit update check` both read it. An isolated run never
    /// goes to the network; it reads the release record placed under APP_LIFECYCLE_CLOUD_DIR.
    static var updateSource: AppUpdateSource { isolated ? .privateCloud(channel: "isolated") : .github(repository: "zengtianli/mackit") }

    // MARK: One factory for the window and the command line

    /// Where the portable settings live: the preference domain that holds the「使用 iCloud 记住配置」switch, and the home
    /// folder whose .config/mackit/portable-preferences.json holds the remembered preset and components.
    struct Store { let defaults: UserDefaults; let home: URL }

    enum Refusal: Error {
        case isolationIncomplete, sandboxHome, sandboxUpgrade
        var code: String { self == .isolationIncomplete ? "isolation_incomplete" : "isolated_home" }
        var message: String {
            switch self {
            case .sandboxUpgrade:
                return "升级替换的是这台 Mac 上装着的 MacKit.app，它不在 --home 目录里：沙盒 HOME 不替换任何 App，也不让运行中的 MacKit 退出。去掉 --home 在本机运行（先加 --dry-run 只看会做什么）；\(Lifecycle.command) update check 在沙盒 HOME 下照常可读。"
            case .isolationIncomplete:
                return "APP_LIFECYCLE_SUPPORT_DIR 已设置（隔离运行）：还需要 \(Lifecycle.suiteVariable)（以 \(Lifecycle.suitePrefix) 开头的一次性偏好域）和 --home <临时目录>（不能是你自己的 HOME），隔离运行才不会碰到你自己的设置。"
            case .sandboxHome:
                return "「配置与更新…」里的几项属于 App 本身：开关在 App 的偏好域，备份在 Application Support，副本在 iCloud Drive，都不在 --home 目录里，所以沙盒 HOME 没有这组设置（演示目录下的 App 也不装这个窗口）。去掉 --home 在本机运行；隔离试跑另设 APP_LIFECYCLE_SUPPORT_DIR、APP_LIFECYCLE_CLOUD_DIR 和 \(Lifecycle.suiteVariable)。"
            }
        }
    }

    /// The .app this executable lives in. Started through a symlink, Bundle.main is the link's folder (no Info.plist, no
    /// identifier); version, build and bundle id then come from the resolved executable's bundle.
    static let hostBundle: Bundle = {
        guard let executable = Bundle.main.executableURL?.resolvingSymlinksInPath() else { return .main }
        let app = executable.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        return (app.pathExtension == "app" ? Bundle(url: app) : nil) ?? .main
    }()
    /// The App's own preference domain. Its main bundle is the product, so that is the standard domain; a start through
    /// a symlink names the host bundle's domain, otherwise the command and the window would each write their own.
    static var hostDefaults: UserDefaults {
        guard let identifier = hostBundle.bundleIdentifier, identifier != Bundle.main.bundleIdentifier else { return .standard }
        return UserDefaults(suiteName: identifier) ?? .standard
    }
    static func ownHome() -> URL { URL(fileURLWithPath: NSHomeDirectory()) }
    static func preferencesFile(_ home: URL) -> URL { home.appendingPathComponent(".config/mackit/portable-preferences.json") }

    /// The command's store. `requested` is the engine's --home (nil: this Mac's own).
    /// - Your own home: the App's preference domain and your own remembered selection.
    /// - An isolated run: a named throwaway preference domain and a home that is not yours, both required.
    ///   (A file-path suite is not kept in step between two running processes; a named domain is.)
    /// - A sandbox --home without the isolation variables: refused, nothing is read.
    static func store(home requested: String?) -> Result<Store, Refusal> {
        let own = ownHome()
        let home = requested.map { URL(fileURLWithPath: ($0 as NSString).expandingTildeInPath) } ?? own
        let isOwn = home.standardizedFileURL.resolvingSymlinksInPath().path == own.standardizedFileURL.resolvingSymlinksInPath().path
        if isolated {
            guard !isOwn, let suite = ProcessInfo.processInfo.environment[suiteVariable], suite.hasPrefix(suitePrefix),
                  suite.count > suitePrefix.count, let defaults = UserDefaults(suiteName: suite) else { return .failure(.isolationIncomplete) }
            return .success(Store(defaults: defaults, home: home))
        }
        guard isOwn else { return .failure(.sandboxHome) }
        return .success(Store(defaults: hostDefaults, home: own))
    }

    static func makeConfiguration(_ store: Store) -> AppConfiguration {
        AppConfiguration(productID: productID, files: [AppConfigurationFile(url: preferencesFile(store.home), keys: ["profile", "components"])],
                         defaults: store.defaults)
    }

    /// AppConfiguration writes the selection file itself, not through the engine (cli.dump keeps it owner-only):
    /// put the mode back after an import or a sync wrote it.
    static func keepPrivate(_ store: Store) {
        try? FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: preferencesFile(store.home).path)
    }

    // MARK: App side

    /// MacKitApp.init on the owner's home, and the follow probe on an isolated store: the window, re-reading when an
    /// import or a sync brought another selection, and following the command line.
    @MainActor @discardableResult
    static func installApp(model: AppModel, store: Store) -> AppConfiguration {
        let configuration = makeConfiguration(store)
        configuration.onChange = { [weak model] in
            keepPrivate(store)
            Task { @MainActor in if let model, !model.busy { model.refresh() } }
        }
        AppLifecycleUI.install(name: name, configuration: configuration, updateSource: updateSource)
        // `mackit config sync on|off` and `mackit config import` run in another process. The running window follows them
        // (the switch, the status line, the imported selection) and never stores the switch itself: the command is its
        // only writer besides the window's own control.
        AppLifecycleCLI.follow(configuration)
        return configuration
    }

    // MARK: Command side

    static func product(_ store: Store?) -> AppLifecycleCLI.Product {
        var product = AppLifecycleCLI.Product(command: command, name: name, configuration: store.map(makeConfiguration), updateSource: updateSource)
        product.bundle = hostBundle
        if let store { product.changed = { keepPrivate(store) } }
        return product
    }

    /// `MacKit [--home <dir>] config …` and `MacKit [--home <dir>] update …`, the words after `mackit` as the engine
    /// forwards them. Returns the exit code, or nil when the arguments are not one of these (the caller starts the app).
    /// Nothing here creates an NSApplication: no window, no Dock icon, no prompt. A running MacKit is left alone by
    /// every command but `update install --yes`, which asks it to quit and reopens it, as the window's own button does.
    static func command(_ arguments: [String]) -> Int32? {
        var words = Array(arguments.dropFirst())
        var home: String?
        if words.count >= 2, words[0] == "--home" { home = words[1]; words.removeFirst(2) }
        guard AppLifecycleCLI.handles(words.first) else { return nil }
        switch store(home: home) {
        case .success(let store):
            return AppLifecycleCLI.run(words, product: product(store))
        case .failure(var refusal):
            // `update check` reads this bundle's version and the release channel, and the help reads nothing: neither needs
            // the settings. `update install` is not a read: it replaces the installed App and quits a running one, which a
            // sandbox --home promises never to do, so it is refused there like the settings are (--dry-run included).
            let installs = words.first == "update" && words.dropFirst().first(where: { !$0.hasPrefix("-") }) == "install"
            if words.contains("--help") || words.contains("-h") || (words.first == "update" && !installs) {
                return AppLifecycleCLI.run(words, product: product(nil))
            }
            if installs, refusal == .sandboxHome { refusal = .sandboxUpgrade }
            let positionals = words.dropFirst().filter { !$0.hasPrefix("-") }
            let name = (words.first ?? "") + " " + (positionals.first ?? "status")
            if words.contains("--json"),
               let data = try? JSONSerialization.data(withJSONObject: ["ok": false, "command": name, "error": ["code": refusal.code, "message": refusal.message]],
                                                      options: [.sortedKeys, .prettyPrinted, .withoutEscapingSlashes]) {
                print(String(decoding: data, as: UTF8.self))
            } else { fputs(refusal.message + "\n", stderr) }
            return 1
        }
    }

    // MARK: Follow probe

    /// `MacKit --lifecycle-follow-probe <state file> --home <isolated home>`: this executable as the running App, for
    /// tests/test_lifecycle_cli.py. It exists for an isolated run only and exits at once otherwise, before any NSApplication.
    static func probe(_ arguments: [String]) -> Never {
        func value(_ flag: String) -> String? { arguments.firstIndex(of: flag).flatMap { arguments.count > $0 + 1 ? arguments[$0 + 1] : nil } }
        guard isolated, let path = value(probeFlag), case .success(let store) = store(home: value("--home")) else {
            fputs("\(probeFlag) runs only in an isolated run: APP_LIFECYCLE_SUPPORT_DIR, \(suiteVariable) (a throwaway preference domain starting with \(suitePrefix)) and --home <a temporary folder, not your own home> are all required.\n", stderr)
            exit(64)
        }
        MainActor.assumeIsolated {
            let app = NSApplication.shared
            app.setActivationPolicy(.prohibited)   // no Dock icon, no menu bar, nothing can be ordered in
            FollowProbe.start(state: URL(fileURLWithPath: path), store: store)
            app.run()
        }
        exit(0)
    }
}

/// The running App of the lifecycle test: the production model and the production `Lifecycle.installApp`, on the
/// isolated store. The shared window is built the way the menu item builds it and never shown. What the configuration,
/// the window's own switch and the model hold is written to the state file for the test to poll; the test reads the
/// stored values themselves through fresh processes.
@MainActor private enum FollowProbe {
    static var model: AppModel?
    static var configuration: AppConfiguration?
    static var control: NSControl?
    static var built: [String: Bool] = [:]
    static var state: URL?
    static var timer: Timer?
    static var changes = 0
    static var tick = 0

    static func start(state: URL, store: Lifecycle.Store) {
        self.state = state
        // An isolated home is a demo home to the model: it never seeds or stores a selection of its own.
        let model = AppModel(home: store.home.path)
        self.model = model
        let configuration = Lifecycle.installApp(model: model, store: store)
        self.configuration = configuration
        let production = configuration.onChange
        configuration.onChange = { changes += 1; production?() }
        do { built = try AppLifecycleUI.shared.offscreenSnapshot(to: state.deletingPathExtension().appendingPathExtension("png")) }
        catch { fputs("lifecycle window: \(error.localizedDescription)\n", stderr); exit(1) }
        control = NSApp.windows.lazy.compactMap { cloudSwitch(in: $0.contentView) }.first
        model.refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { _ in MainActor.assumeIsolated { write() } }
    }

    /// The「使用 iCloud 记住配置」control of the shared window: a switch in the current shared source, a checkbox in older copies.
    static func cloudSwitch(in view: NSView?) -> NSControl? {
        guard let view else { return nil }
        if let toggle = view as? NSSwitch { return toggle }
        if let button = view as? NSButton, button.title == "使用 iCloud 记住配置" { return button }
        for child in view.subviews { if let found = cloudSwitch(in: child) { return found } }
        return nil
    }

    static func write() {
        guard let state, let configuration, let model else { return }
        tick += 1
        let shown = (control as? NSSwitch)?.state ?? (control as? NSButton)?.state
        let seen: [String: Any] = ["enabled": configuration.enabled, "status": configuration.status, "changes": changes, "tick": tick,
                                   "window_switch": shown.map { $0 == .on } ?? NSNull(), "window_built": built,
                                   "windows_on_screen": NSApp.windows.filter(\.isVisible).count,
                                   "policy_prohibited": NSApp.activationPolicy() == .prohibited, "active": NSApp.isActive,
                                   "loaded": model.snapshot != nil, "busy": model.busy, "error": model.error,
                                   "profile": model.profile, "components": model.selected.sorted()]
        try? JSONSerialization.data(withJSONObject: seen, options: [.sortedKeys]).write(to: state, options: .atomic)
    }
}
