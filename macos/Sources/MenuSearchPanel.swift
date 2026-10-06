import AppKit
import ApplicationServices
import Darwin

private final class MenuCommandPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
    override func cancelOperation(_ sender: Any?) { close() }
}

private final class MenuCommandTable: NSTableView {
    var execute: (() -> Void)?
    override func keyDown(with event: NSEvent) {
        if event.keyCode == 36 || event.keyCode == 76 { execute?() }
        else { super.keyDown(with: event) }
    }
}

/// A nonactivating key panel leaves the target application's menu bar in place.
/// Every launch is fresh; there is no daemon, filesystem menu cache or Raycast dependency.
@MainActor final class MenuSearchPanel: NSObject, NSTableViewDataSource, NSTableViewDelegate, NSSearchFieldDelegate, NSWindowDelegate {
    static var current: MenuSearchPanel?
    private let panel: NSPanel
    private let search = NSSearchField()
    private let table = MenuCommandTable()
    private let info = NSTextField(labelWithString: "")
    private let state = NSTextField(labelWithString: "正在读取菜单…")
    private let appLabel = NSTextField(labelWithString: "")
    private let refreshButton = NSButton(title: "刷新", target: nil, action: nil)
    private let settingsButton = NSButton(title: "辅助功能设置", target: nil, action: nil)
    private let queue = DispatchQueue(label: "cyou.tianli.mackit.menu-reader", qos: .userInitiated)
    private var reader: MenuReader?
    private var snapshot: MenuSnapshot?
    private var index = MenuSearchIndex([])
    private var shown: [MenuCommand] = []
    private var busy = false
    private var finished = false
    private var executing = false
    private var lockFD: Int32 = -1
    private var observer: NSObjectProtocol?
    private var generation = 0
    private let testing: Bool
    var testExecuted: [String] = []
    var testCancelled = false

    init(testing: Bool = false) {
        self.testing = testing
        panel = MenuCommandPanel(contentRect: NSRect(x: 0, y: 0, width: 780, height: 570),
                                 styleMask: [.titled, .closable, .resizable, .nonactivatingPanel], backing: .buffered, defer: false)
        super.init()
        panel.title = "MacKit · 菜单搜索"
        panel.isReleasedWhenClosed = false
        panel.isFloatingPanel = true
        panel.becomesKeyOnlyIfNeeded = false
        panel.hidesOnDeactivate = false
        panel.level = .floating
        panel.collectionBehavior = [.moveToActiveSpace, .fullScreenAuxiliary, .transient, .ignoresCycle]
        panel.minSize = NSSize(width: 600, height: 380)
        panel.delegate = self
        panel.backgroundColor = .windowBackgroundColor
        let container = NSView()
        panel.contentView = container
        let stack = NSStackView()
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 14
        stack.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 20),
            stack.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -20),
            stack.topAnchor.constraint(equalTo: container.topAnchor, constant: 18),
            stack.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -16)
        ])
        appLabel.font = .systemFont(ofSize: 15, weight: .semibold)
        info.font = .systemFont(ofSize: 12); info.textColor = .secondaryLabelColor
        let head = NSStackView(views: [appLabel, NSView(), info, refreshButton])
        head.orientation = .horizontal; head.spacing = 12
        stack.addArrangedSubview(head)
        search.placeholderString = "搜索当前 App 的菜单命令…"
        search.sendsSearchStringImmediately = true
        search.sendsWholeSearchString = false
        search.font = .systemFont(ofSize: 17)
        search.delegate = self
        stack.addArrangedSubview(search)
        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true; scroll.autohidesScrollers = true
        scroll.borderType = .noBorder; scroll.drawsBackground = false
        let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("command"))
        column.resizingMask = .autoresizingMask
        table.addTableColumn(column)
        table.headerView = nil; table.rowHeight = 54
        table.style = .fullWidth; table.backgroundColor = .clear
        table.dataSource = self; table.delegate = self
        table.allowsMultipleSelection = false
        table.target = self; table.doubleAction = #selector(executeSelection)
        table.execute = { [weak self] in self?.executeSelection() }
        table.columnAutoresizingStyle = .lastColumnOnlyAutoresizingStyle
        scroll.documentView = table
        stack.addArrangedSubview(scroll)
        state.font = .systemFont(ofSize: 12); state.textColor = .secondaryLabelColor
        state.lineBreakMode = .byWordWrapping; state.maximumNumberOfLines = 3
        state.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        let hints = NSTextField(labelWithString: "↑↓ 选择    ↩ 执行    Esc 关闭")
        hints.font = .systemFont(ofSize: 12); hints.textColor = .secondaryLabelColor
        let foot = NSStackView(views: [state, NSView(), hints])
        foot.orientation = .horizontal; foot.spacing = 12
        stack.addArrangedSubview(foot)
        settingsButton.target = self; settingsButton.action = #selector(openSettings)
        settingsButton.isHidden = true; stack.addArrangedSubview(settingsButton)
        refreshButton.target = self; refreshButton.action = #selector(refresh)
        for view in [head, search, scroll, foot] {
            view.translatesAutoresizingMaskIntoConstraints = false
            view.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        }
        search.heightAnchor.constraint(equalToConstant: 36).isActive = true
        scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 180).isActive = true
        scroll.setContentHuggingPriority(.defaultLow, for: .vertical)
    }

    static func launch() {
        do {
            let target = try MenuReader.target(pid: MenuSearchCLI.pid())
            let controller = MenuSearchPanel()
            guard controller.acquireLock() else { exit(0) }
            current = controller
            controller.reader = MenuReader(target: target)
            controller.appLabel.stringValue = target.localizedName ?? "当前 App"
            controller.present()
            controller.refresh()
        } catch { MenuSearchCLI.emit(["error": error.localizedDescription]); exit(1) }
    }

    private func acquireLock() -> Bool {
        let stateDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".local/state/mackit")
        do { try FileManager.default.createDirectory(at: stateDir, withIntermediateDirectories: true) }
        catch { return false }
        let path = stateDir.appendingPathComponent("menu-search.lock").path
        lockFD = open(path, O_CREAT | O_RDWR | O_CLOEXEC | O_NOFOLLOW, S_IRUSR | S_IWUSR)
        guard lockFD >= 0 else { return false }
        let name = Notification.Name("cyou.tianli.mackit.menu-search.\(getuid()).toggle")
        if flock(lockFD, LOCK_EX | LOCK_NB) != 0 {
            DistributedNotificationCenter.default().postNotificationName(name, object: nil, userInfo: nil, deliverImmediately: true)
            Darwin.close(lockFD); lockFD = -1; return false
        }
        observer = DistributedNotificationCenter.default().addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.finish() }
        }
        return true
    }

    private func present() {
        guard !testing else { return }
        let screen = NSScreen.screens.first(where: { NSMouseInRect(NSEvent.mouseLocation, $0.frame, false) }) ?? NSScreen.main
        if let frame = screen?.visibleFrame {
            panel.setFrameOrigin(NSPoint(x: frame.midX - panel.frame.width / 2, y: frame.midY - panel.frame.height / 2 + frame.height * 0.08))
        }
        panel.makeKeyAndOrderFront(nil)
        panel.makeFirstResponder(search)
    }

    @objc private func openSettings() {
        guard !testing else { return }
        NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!)
        finish()
    }

    @objc private func refresh() {
        guard !busy, let reader, !finished else { return }
        busy = true; refreshButton.isEnabled = false
        state.stringValue = "正在读取菜单…"; generation += 1
        let version = generation
        queue.async { [weak self] in
            let result = Result { try reader.scan() }
            DispatchQueue.main.async {
                guard let self, !self.finished, self.generation == version else { return }
                self.busy = false; self.refreshButton.isEnabled = true
                switch result {
                case .success(let snapshot): self.apply(snapshot)
                case .failure(let error):
                    self.snapshot = nil; self.index = MenuSearchIndex([]); self.shown = []
                    self.table.reloadData(); self.info.stringValue = ""
                    self.state.stringValue = error.localizedDescription
                    self.settingsButton.isHidden = AXIsProcessTrusted()
                }
            }
        }
    }

    func apply(_ snapshot: MenuSnapshot) {
        self.snapshot = snapshot
        index = MenuSearchIndex(snapshot.items)
        appLabel.stringValue = snapshot.app
        panel.title = "MacKit · 菜单搜索 · \(snapshot.app)"
        settingsButton.isHidden = true
        filter()
    }

    private func filter() {
        let oldID = table.selectedRow >= 0 && table.selectedRow < shown.count ? shown[table.selectedRow].id : nil
        shown = index.filter(search.stringValue)
        table.reloadData()
        let row = oldID.flatMap { id in shown.firstIndex { $0.id == id } } ?? (shown.isEmpty ? nil : 0)
        if let row { table.selectRowIndexes(IndexSet(integer: row), byExtendingSelection: false); table.scrollRowToVisible(row) }
        else { table.deselectAll(nil) }
        if let snapshot {
            info.stringValue = "\(shown.count) / \(snapshot.items.count) 条 · \(Int(snapshot.durationMS.rounded())) ms"
            state.stringValue = !snapshot.complete ? snapshot.warnings.joined(separator: " ") : (shown.isEmpty ? "没有匹配的菜单命令" : "仅搜索 \(snapshot.app) 的菜单")
        }
    }

    func numberOfRows(in tableView: NSTableView) -> Int { shown.count }
    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        guard shown.indices.contains(row) else { return nil }
        let command = shown[row]
        let cell = NSTableCellView()
        let title = NSTextField(labelWithString: (command.checked ? "✓  " : "") + command.title)
        title.font = .systemFont(ofSize: 14, weight: .medium)
        title.textColor = command.enabled ? .labelColor : .tertiaryLabelColor
        let path = NSTextField(labelWithString: command.location)
        path.font = .systemFont(ofSize: 11); path.textColor = .secondaryLabelColor
        path.lineBreakMode = .byTruncatingMiddle
        let shortcut = NSTextField(labelWithString: command.shortcut + (command.enabled ? "" : "  不可用"))
        shortcut.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
        shortcut.textColor = .secondaryLabelColor
        let labels = NSStackView(views: [title, path])
        labels.orientation = .vertical; labels.alignment = .leading; labels.spacing = 4
        labels.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        let rowStack = NSStackView(views: [labels, NSView(), shortcut])
        rowStack.orientation = .horizontal; rowStack.spacing = 12
        rowStack.translatesAutoresizingMaskIntoConstraints = false
        cell.addSubview(rowStack); cell.textField = title
        cell.toolTip = command.fullPath
        NSLayoutConstraint.activate([
            rowStack.leadingAnchor.constraint(equalTo: cell.leadingAnchor, constant: 10),
            rowStack.trailingAnchor.constraint(equalTo: cell.trailingAnchor, constant: -10),
            rowStack.centerYAnchor.constraint(equalTo: cell.centerYAnchor)
        ])
        return cell
    }

    func controlTextDidChange(_ notification: Notification) { filter() }
    func control(_ control: NSControl, textView: NSTextView, doCommandBy selector: Selector) -> Bool {
        if textView.hasMarkedText() { return false }
        // Preserve standard text editing (including modifier-arrow movements).
        if NSApp.currentEvent?.modifierFlags.intersection([.command, .option, .control]).isEmpty == false { return false }
        switch NSStringFromSelector(selector) {
        case "moveDown:": move(1); return true
        case "moveUp:": move(-1); return true
        case "insertNewline:": executeSelection(); return true
        case "cancelOperation:": finish(); return true
        default: return false
        }
    }
    private func move(_ step: Int) {
        guard !shown.isEmpty else { return }
        let row = min(shown.count - 1, max(0, table.selectedRow + step))
        table.selectRowIndexes(IndexSet(integer: row), byExtendingSelection: false)
        table.scrollRowToVisible(row)
    }

    @objc private func executeSelection() {
        guard !busy, shown.indices.contains(table.selectedRow) else { return }
        let command = shown[table.selectedRow]
        guard command.enabled else { state.stringValue = "这个命令当前不可用"; return }
        if testing { testExecuted.append(command.id); return }
        guard let reader, let current = NSWorkspace.shared.frontmostApplication,
              current.processIdentifier == reader.target.processIdentifier else {
            state.stringValue = "当前 App 已变化，请关闭面板后重新搜索。"; return
        }
        busy = true; executing = true; refreshButton.isEnabled = false
        // Return the key focus before pressing, without activating or switching the target app.
        panel.orderOut(nil)
        queue.async { [weak self] in
            let result = Result { try reader.perform(command) }
            DispatchQueue.main.async {
                guard let self, !self.finished else { return }
                switch result {
                case .success: self.finish()
                case .failure(let error):
                    self.busy = false; self.executing = false; self.refreshButton.isEnabled = true
                    self.present(); self.state.stringValue = error.localizedDescription
                }
            }
        }
    }
    func windowDidResignKey(_ notification: Notification) { if !executing { finish() } }
    func windowWillClose(_ notification: Notification) { finish() }
    private func finish() {
        guard !finished else { return }
        finished = true; generation += 1
        if testing { testCancelled = true; return }
        panel.orderOut(nil)
        if let observer { DistributedNotificationCenter.default().removeObserver(observer) }
        if lockFD >= 0 { flock(lockFD, LOCK_UN); Darwin.close(lockFD); lockFD = -1 }
        NSApp.terminate(nil)
    }

    /// Exercises the actual panel/delegate, without showing windows or performing external menu actions.
    static func selfTest() {
        let args = CommandLine.arguments
        guard let i = args.firstIndex(of: "--output"), args.count > i + 1 else {
            fputs("--menu-self-test requires --output DIR\n", stderr); exit(2)
        }
        do {
            let out = URL(fileURLWithPath: args[i + 1])
            try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
            let items = [
                MenuCommand(id: "0", title: "Export as PDF…", path: ["File", "Export as PDF…"], shortcut: "⇧⌘E", enabled: true, checked: false),
                MenuCommand(id: "1", title: "JavaScript Console", path: ["View", "Developer", "JavaScript Console"], shortcut: "⌥⌘J", enabled: true, checked: false),
                MenuCommand(id: "2", title: "Use Selection for Find", path: ["Edit", "Find", "Use Selection for Find"], shortcut: "⌘E", enabled: false, checked: false),
                MenuCommand(id: "3", title: "写笔记", path: ["文件", "写笔记"], shortcut: "⌘N", enabled: true, checked: false),
                MenuCommand(id: "4", title: "Date Modified", path: ["View", "Group Stacks By", "Date Modified"], shortcut: "", enabled: true, checked: true),
                MenuCommand(id: "5", title: "Date Modified", path: ["View", "Sort Stacks By", "Date Modified"], shortcut: "", enabled: true, checked: false),
                MenuCommand(id: "6", title: "Date Modified", path: ["View", "Clean Up By", "Date Modified"], shortcut: "", enabled: true, checked: false)
            ]
            let snapshot = MenuSnapshot(ok: true, pid: 0, app: "Safari", bundleID: "fixture", durationMS: 168, complete: true, warnings: [], items: items)
            let ui = MenuSearchPanel(testing: true)
            ui.apply(snapshot)
            var checks: [String: Bool] = [:]
            checks["empty_lists_all"] = ui.shown.count == items.count
            checks["distinct_duplicate_paths"] = Set(MenuSearchIndex(items).filter("date modified").map(\.fullPath)).count == 3
            checks["fuzzy_multi_token"] = MenuSearchIndex(items).filter("exp pdf").first?.id == "0"
            checks["path_search"] = MenuSearchIndex(items).filter("view developer").first?.id == "1"
            checks["chinese"] = MenuSearchIndex(items).filter("写笔记").first?.id == "3"
            ui.search.stringValue = "use selection"; ui.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification))
            ui.executeSelection(); checks["disabled_not_executed"] = ui.testExecuted.isEmpty
            ui.search.stringValue = "exp pdf"; ui.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification))
            let editor = NSTextView()
            _ = ui.control(ui.search, textView: editor, doCommandBy: NSSelectorFromString("insertNewline:"))
            checks["enter_dispatch"] = ui.testExecuted == ["0"]
            ui.search.stringValue = ""; ui.filter()
            _ = ui.control(ui.search, textView: editor, doCommandBy: NSSelectorFromString("moveDown:"))
            checks["down_browses"] = ui.table.selectedRow == 1
            _ = ui.control(ui.search, textView: editor, doCommandBy: NSSelectorFromString("moveUp:"))
            checks["up_browses"] = ui.table.selectedRow == 0
            checks["editing_preserved"] = !ui.control(ui.search, textView: editor, doCommandBy: NSSelectorFromString("deleteWordBackward:"))
            editor.setMarkedText("写", selectedRange: NSRange(location: 1, length: 0), replacementRange: NSRange(location: NSNotFound, length: 0))
            checks["ime_return_preserved"] = !ui.control(ui.search, textView: editor, doCommandBy: NSSelectorFromString("insertNewline:"))
            editor.unmarkText()
            let updated = MenuCommand(id: "0", title: "Hide Status Bar", path: ["View", "Hide Status Bar"], shortcut: "⌘/", enabled: true, checked: false)
            ui.apply(MenuSnapshot(ok: true, pid: 0, app: "Safari", bundleID: "fixture", durationMS: 10, complete: true, warnings: [], items: [updated]))
            checks["fresh_dynamic_titles"] = ui.shown.first?.title == "Hide Status Bar" && !ui.shown.contains { $0.title.contains("Export") }
            let renderSnapshot: MenuSnapshot
            if let pid = MenuSearchCLI.pid() { renderSnapshot = try MenuReader(target: MenuReader.target(pid: pid)).scan() }
            else { renderSnapshot = snapshot }
            for (name, appearanceName) in [("light", NSAppearance.Name.aqua), ("dark", .darkAqua)] {
                let preview = MenuSearchPanel(testing: true)
                guard let appearance = NSAppearance(named: appearanceName) else { continue }
                preview.panel.appearance = appearance
                preview.apply(renderSnapshot)
                guard let view = preview.panel.contentView else { continue }
                view.layoutSubtreeIfNeeded()
                // Let AppKit instantiate table rows and resolve inherited appearance offscreen.
                RunLoop.current.run(until: Date().addingTimeInterval(0.02))
                view.layoutSubtreeIfNeeded()
                var rendered = false
                var renderedPNG: Data?
                appearance.performAsCurrentDrawingAppearance {
                    guard let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) else { return }
                    view.cacheDisplay(in: view.bounds, to: bitmap)
                    view.needsDisplay = true
                    view.cacheDisplay(in: view.bounds, to: bitmap)
                    // AppKit's offscreen cache omits the compositor's window background.
                    guard let source = bitmap.cgImage,
                          let context = CGContext(data: nil, width: source.width, height: source.height, bitsPerComponent: 8,
                                                  bytesPerRow: source.width * 4, space: CGColorSpaceCreateDeviceRGB(),
                                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue) else { return }
                    let rect = CGRect(x: 0, y: 0, width: source.width, height: source.height)
                    context.setFillColor(NSColor.windowBackgroundColor.usingColorSpace(.deviceRGB)!.cgColor)
                    context.fill(rect); context.draw(source, in: rect)
                    guard let image = context.makeImage(), let png = NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:]) else { return }
                    renderedPNG = png
                    rendered = source.width > 500 && source.height > 300
                }
                let prefix = MenuSearchCLI.pid() == nil ? "menu-search" : "native-\(renderSnapshot.app.replacingOccurrences(of: " ", with: "-"))"
                try renderedPNG?.write(to: out.appendingPathComponent("\(prefix)-\(name).png"))
                checks["render_\(name)"] = rendered
            }
            _ = ui.control(ui.search, textView: editor, doCommandBy: NSSelectorFromString("cancelOperation:"))
            checks["esc_cancels"] = ui.testCancelled
            let passed = checks.values.allSatisfy { $0 }
            let result: [String: Any] = ["ok": passed, "environment": "offscreen-production-panel", "external_actions": 0,
                                      "checks": checks, "limitations": ["Physical hotkey and external App menu execution require Computer Use while the user yields the computer."]]
            let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: out.appendingPathComponent("menu-search-self-test.json"))
            print(String(data: data, encoding: .utf8)!)
            exit(passed ? 0 : 1)
        } catch { fputs("\(error.localizedDescription)\n", stderr); exit(1) }
    }
}
