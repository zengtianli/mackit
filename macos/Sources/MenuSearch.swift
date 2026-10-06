import AppKit
import ApplicationServices

/// Product implementation, independent of Raycast. Scanning never opens menus or changes focus.
struct MenuCommand: Codable, Equatable {
    let id: String
    let title: String
    let path: [String]
    let shortcut: String
    let enabled: Bool
    let checked: Bool
    var location: String { path.dropLast().joined(separator: " › ") }
    var fullPath: String { path.joined(separator: " › ") }
}

struct MenuSnapshot: Codable {
    let ok: Bool
    let pid: Int32
    let app: String
    let bundleID: String
    let durationMS: Double
    let complete: Bool
    let warnings: [String]
    let items: [MenuCommand]
}

enum MenuSearchError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case let .message(text) = self { return text }; return nil }
}

// Mutable AX state is confined to the panel's single serial queue (or a synchronous CLI call).
final class MenuReader: @unchecked Sendable {
    let target: NSRunningApplication
    private var elements: [String: AXUIElement] = [:]
    private var deadline = Date.distantFuture
    private var warnings = Set<String>()
    init(target: NSRunningApplication) { self.target = target }

    static func target(pid: Int32? = nil) throws -> NSRunningApplication {
        if let pid {
            guard pid > 0, let app = NSRunningApplication(processIdentifier: pid), !app.isTerminated else {
                throw MenuSearchError.message("目标 App 已退出。请重新打开菜单搜索。")
            }
            return app
        }
        guard let app = NSWorkspace.shared.menuBarOwningApplication ?? NSWorkspace.shared.frontmostApplication else {
            throw MenuSearchError.message("没有找到当前 App。")
        }
        return app
    }

    private func value(_ element: AXUIElement, _ key: String) -> CFTypeRef? {
        var result: CFTypeRef?
        let code = AXUIElementCopyAttributeValue(element, key as CFString, &result)
        if code == .cannotComplete { warnings.insert("部分菜单暂未响应，请刷新后重试。") }
        return code == .success ? result : nil
    }
    private func children(_ element: AXUIElement) -> [AXUIElement] {
        value(element, kAXChildrenAttribute) as? [AXUIElement] ?? []
    }
    private func title(_ element: AXUIElement) -> String {
        (value(element, kAXTitleAttribute) as? String ?? "").replacingOccurrences(of: "\n", with: " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }
    private func shortcut(_ element: AXUIElement) -> String {
        let char = value(element, kAXMenuItemCmdCharAttribute) as? String ?? ""
        let key = value(element, kAXMenuItemCmdVirtualKeyAttribute) as? Int ?? -1
        let mods = value(element, kAXMenuItemCmdModifiersAttribute) as? Int ?? 0
        let special: [Int: String] = [36:"↩",48:"⇥",49:"Space",51:"⌫",53:"⎋",76:"⌤",117:"⌦",123:"←",124:"→",125:"↓",126:"↑",
            122:"F1",120:"F2",99:"F3",118:"F4",96:"F5",97:"F6",98:"F7",100:"F8",101:"F9",109:"F10",103:"F11",111:"F12"]
        let functionCharacters: [UInt32: String] = [0xf700:"↑",0xf701:"↓",0xf702:"←",0xf703:"→",0xf728:"⌦",0xf729:"Home",0xf72b:"End",0xf72c:"Page Up",0xf72d:"Page Down"]
        let base = char.isEmpty ? (special[key] ?? "") : (char.unicodeScalars.first.flatMap { functionCharacters[$0.value] } ?? (char == "\u{7f}" ? "⌦" : char.uppercased()))
        guard !base.isEmpty else { return "" }
        return (mods & 4 != 0 ? "⌃" : "") + (mods & 2 != 0 ? "⌥" : "") + (mods & 1 != 0 ? "⇧" : "") + (mods & 8 == 0 ? "⌘" : "") + base
    }

    func scan() throws -> MenuSnapshot {
        guard AXIsProcessTrusted() else {
            throw MenuSearchError.message("菜单搜索需要 MacKit 的辅助功能权限。请在系统设置的隐私与安全性中授权 MacKit，再重新打开。")
        }
        guard !target.isTerminated else { throw MenuSearchError.message("目标 App 已退出。") }
        let start = Date()
        deadline = start.addingTimeInterval(5)
        warnings.removeAll(); elements.removeAll()
        let app = AXUIElementCreateApplication(target.processIdentifier)
        AXUIElementSetMessagingTimeout(app, 0.3)
        guard let menuValue = value(app, kAXMenuBarAttribute), CFGetTypeID(menuValue) == AXUIElementGetTypeID() else {
            throw MenuSearchError.message("\(target.localizedName ?? "当前 App") 没有提供可读取的菜单栏。")
        }
        let menu = unsafeBitCast(menuValue, to: AXUIElement.self)
        var items: [MenuCommand] = []
        func visit(_ element: AXUIElement, path: [String], indices: [Int], ancestorsEnabled: Bool, depth: Int) {
            guard Date() < deadline else { warnings.insert("菜单读取超过 5 秒，结果不完整。请刷新后重试。"); return }
            guard depth < 64, items.count < 10000 else { warnings.insert("菜单结构过大，结果不完整。"); return }
            let role = value(element, kAXRoleAttribute) as? String ?? ""
            let name = title(element)
            let enabled = ancestorsEnabled && (value(element, kAXEnabledAttribute) as? Bool ?? true)
            let named = role == kAXMenuItemRole || role == kAXMenuBarItemRole
            let next = named && !name.isEmpty ? path + [name] : path
            let nested = children(element)
            if !nested.isEmpty {
                for (i, child) in nested.enumerated() {
                    visit(child, path: next, indices: indices + [i], ancestorsEnabled: enabled, depth: depth + 1)
                }
            } else if role == kAXMenuItemRole, !name.isEmpty {
                let id = indices.map(String.init).joined(separator: ".")
                let checked = !(value(element, kAXMenuItemMarkCharAttribute) as? String ?? "").isEmpty
                items.append(MenuCommand(id: id, title: name, path: next, shortcut: shortcut(element), enabled: enabled, checked: checked))
                elements[id] = element
            }
        }
        for (index, top) in children(menu).enumerated() {
            let name = title(top)
            // System Apple menu isn't a command belonging to the target app.
            if ["Apple", "苹果", ""].contains(name) { continue }
            visit(top, path: [], indices: [index], ancestorsEnabled: true, depth: 0)
        }
        return MenuSnapshot(ok: true, pid: target.processIdentifier, app: target.localizedName ?? "当前 App",
                            bundleID: target.bundleIdentifier ?? "", durationMS: Date().timeIntervalSince(start) * 1000,
                            complete: warnings.isEmpty, warnings: warnings.sorted(), items: items)
    }

    /// Keep the actual AX object, and revalidate its owner, title and state before an explicit user action.
    /// Position indices are only identifiers; they are never replayed into a changed menu tree.
    func perform(_ command: MenuCommand) throws {
        guard command.enabled else { throw MenuSearchError.message("这个命令当前不可用。") }
        guard !target.isTerminated, let element = elements[command.id] else { throw MenuSearchError.message("菜单已经变化，请刷新后重新选择。") }
        var pid: pid_t = 0
        guard AXUIElementGetPid(element, &pid) == .success, pid == target.processIdentifier,
              title(element) == command.title else { throw MenuSearchError.message("菜单已经变化，请刷新后重新选择。") }
        guard value(element, kAXEnabledAttribute) as? Bool == true else { throw MenuSearchError.message("这个命令当前不可用，请刷新菜单。") }
        let result = AXUIElementPerformAction(element, kAXPressAction as CFString)
        guard result == .success else { throw MenuSearchError.message("App 没有执行这个命令（\(result.rawValue)）。请刷新后重试。") }
    }
}

/// Precompute folded strings once per fresh menu snapshot. Tokens can match discontinuous characters.
struct MenuSearchIndex {
    let items: [MenuCommand]
    private let titles: [String]
    private let paths: [String]
    init(_ items: [MenuCommand]) {
        self.items = items
        titles = items.map { Self.fold($0.title) }
        paths = items.map { Self.fold($0.fullPath) }
    }
    private static func fold(_ text: String) -> String {
        text.folding(options: [.caseInsensitive, .diacriticInsensitive, .widthInsensitive], locale: nil).lowercased()
    }
    private static func score(_ needle: String, in text: String) -> Int? {
        if text == needle { return 1000 }
        if text.hasPrefix(needle) { return 800 }
        if text.contains(needle) { return 600 }
        var at = needle.startIndex
        var gaps = 0
        for character in text {
            if character == needle[at] {
                at = needle.index(after: at)
                if at == needle.endIndex { return max(1, 300 - gaps) }
            } else { gaps += 1 }
        }
        return nil
    }
    func filter(_ query: String) -> [MenuCommand] {
        let tokens = Self.fold(query).split(whereSeparator: { $0.isWhitespace }).map(String.init)
        guard !tokens.isEmpty else { return items }
        var ranked: [(Int, Int)] = []
        for i in items.indices {
            var total = 0
            var matched = true
            for token in tokens {
                if let s = Self.score(token, in: titles[i]) { total += s + 200 }
                else if let s = Self.score(token, in: paths[i]) { total += s }
                else { matched = false; break }
            }
            if matched { ranked.append((i, total)) }
        }
        ranked.sort { $0.1 == $1.1 ? $0.0 < $1.0 : $0.1 > $1.1 }
        return ranked.map { items[$0.0] }
    }
}

enum MenuSearchCLI {
    static func emit<T: Encodable>(_ value: T) {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        if let data = try? encoder.encode(value), let text = String(data: data, encoding: .utf8) { print(text) }
    }
    static func pid() -> Int32? {
        let args = CommandLine.arguments
        guard let i = args.firstIndex(of: "--pid"), args.count > i + 1 else { return nil }
        return Int32(args[i + 1])
    }
    static func readOnly() -> Bool {
        let args = CommandLine.arguments
        if args.contains("--menu-status") {
            emit(["ok": true, "accessibility": AXIsProcessTrusted()]); return true
        }
        if args.contains("--menu-scan") || args.contains("--menu-execute") {
            do {
                let reader = MenuReader(target: try MenuReader.target(pid: pid()))
                let snapshot = try reader.scan()
                if args.contains("--menu-execute") {
                    guard snapshot.complete, let i = args.firstIndex(of: "--path-json"), args.count > i + 1,
                          let data = args[i + 1].data(using: .utf8),
                          let path = try? JSONDecoder().decode([String].self, from: data), !path.isEmpty else {
                        throw MenuSearchError.message("执行需要完整菜单路径（--path-json）。")
                    }
                    let matches = snapshot.items.filter { $0.path == path }
                    guard matches.count == 1 else { throw MenuSearchError.message("完整路径未唯一匹配，请重新读取菜单。") }
                    guard NSWorkspace.shared.frontmostApplication?.processIdentifier == snapshot.pid else {
                        throw MenuSearchError.message("目标 App 不在前台，未执行命令。")
                    }
                    try reader.perform(matches[0])
                    emit(["ok": true]); return true
                }
                emit(snapshot)
                if !snapshot.complete { exit(1) }
            } catch {
                struct Failure: Encodable { let ok = false; let error: String }
                emit(Failure(error: error.localizedDescription)); exit(1)
            }
            return true
        }
        return false
    }
}
