import Foundation

struct Component: Decodable, Identifiable { let id: String; let label: String; let desktop: Bool }
struct ConfigFile: Decodable, Identifiable { let id: String; let path: String }
struct Transaction: Decodable, Identifiable { let id: String; let status: String; let changed: Int; let profile: String }
struct KeyBinding: Decodable, Identifiable {
    let component: String; let key: String; let description: String; let mode: String; let source: String
    let profile: String?
    var advanced: Bool { description.hasPrefix("编码跳行") }
    var id: String { [component, key, mode, profile ?? "", description, source].joined(separator: "|") }
}
struct Snapshot: Decodable {
    let installed: Bool; let profile: String; let selected: [String]; let sourceRoot: String
    let sourceVersion: String; let appVersion: String; let components: [Component]
    let profiles: [String: [String]]; let transactions: [Transaction]; let files: [ConfigFile]
    let keys: [KeyBinding]; let brew: String
}
struct Dependency: Decodable, Identifiable { let id: String; let kind: String; let installed: Bool; let label: String }
struct PlanEntry: Decodable, Identifiable {
    let component: String; let source: String; let target: String; let action: String
    var id: String { target }
    var label: String { action == "unchanged" ? "已就绪" : action == "install" ? "新建配置" : "备份后安装" }
}
struct InstallPlan: Decodable { let profile: String; let root: String; let entries: [PlanEntry] }
struct Preview: Decodable { let plan: InstallPlan; let token: String; let dependencies: [Dependency] }
struct Diagnosis: Decodable { let profile: String; let issues: [String]; let note: String }
struct DiagnosisResponse: Decodable { let diagnosis: Diagnosis }
struct FileResponse: Decodable { let path: String; let content: String; let digest: String; let message: String? }
struct MessageResponse: Decodable { let message: String }
struct DependenciesResponse: Decodable { let dependencies: [Dependency] }
enum Page: String, CaseIterable, Identifiable {
    case install = "安装配置", keys = "快捷键", files = "配置文件", health = "检查与恢复", window = "窗口"
    var id: String { rawValue }
    var icon: String {
        switch self { case .install: "shippingbox"; case .keys: "command"; case .window: "rectangle.split.2x2"; case .files: "doc.text"; case .health: "clock.arrow.circlepath" }
    }
}

// 窗口页（yabai + skhd）。数据源是引擎的 settings.json / hotkeys.json，App 只编辑草稿。
struct ServiceState: Decodable { let installed: Bool; let running: Bool; let version: String }
struct SettingSpec: Decodable, Identifiable {
    let key: String; let kind: String; let choices: [String]; let range: [Double]; let label: String; let help: String
    var id: String { key }
}
struct WindowAction: Decodable, Identifiable { let id: String; let label: String }
struct HotkeyRow: Codable, Identifiable, Equatable {
    var uid = UUID()
    var key: String; var action: String = ""; var command: String = ""; var note: String = ""
    var id: UUID { uid }
    enum CodingKeys: String, CodingKey { case key, action, command, note }
    init(key: String, action: String = "", command: String = "", note: String = "") { self.key = key; self.action = action; self.command = command; self.note = note }
    init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        key = try c.decode(String.self, forKey: .key)
        action = try c.decodeIfPresent(String.self, forKey: .action) ?? ""
        command = try c.decodeIfPresent(String.self, forKey: .command) ?? ""
        note = try c.decodeIfPresent(String.self, forKey: .note) ?? ""
    }
    var payload: [String: Any] {
        var p: [String: Any] = ["key": key]
        if !action.isEmpty { p["action"] = action } else { p["command"] = command }
        if !note.isEmpty { p["note"] = note }
        return p
    }
}
struct AppRule: Codable, Identifiable, Equatable {
    var uid = UUID()
    var app: String; var manage: String = ""; var sticky: String = ""; var space: Int = 0
    var id: UUID { uid }
    enum CodingKeys: String, CodingKey { case app, manage, sticky, space }
    init(app: String) { self.app = app }
    init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        app = try c.decode(String.self, forKey: .app)
        manage = try c.decodeIfPresent(String.self, forKey: .manage) ?? ""
        sticky = try c.decodeIfPresent(String.self, forKey: .sticky) ?? ""
        space = try c.decodeIfPresent(Int.self, forKey: .space) ?? 0
    }
    var payload: [String: Any] {
        var p: [String: Any] = ["app": app]
        if !manage.isEmpty { p["manage"] = manage }
        if !sticky.isEmpty { p["sticky"] = sticky }
        if space > 0 { p["space"] = space }
        return p
    }
}
/// 设置值统一按字符串编辑；空串 = 不写入（沿用 yabai 默认）。
struct WindowDraft: Equatable {
    var settings: [String: String] = [:]
    var hotkeys: [HotkeyRow] = []
    var rules: [AppRule] = []
    static func == (a: Self, b: Self) -> Bool {
        a.settings.filter { !$0.value.isEmpty } == b.settings.filter { !$0.value.isEmpty }
        && a.hotkeys.map(\.payloadKey) == b.hotkeys.map(\.payloadKey) && a.rules.map(\.payloadKey) == b.rules.map(\.payloadKey)
    }
}
extension HotkeyRow { var payloadKey: String { [key, action, command, note].joined(separator: "\u{1}") } }
extension AppRule { var payloadKey: String { [app, manage, sticky, String(space)].joined(separator: "\u{1}") } }
struct WindowSnapshot: Decodable {
    let settings: [String: SettingValue]; let rules: [AppRule]; let hotkeys: [HotkeyRow]
    let yabai: ServiceState; let skhd: ServiceState; let live: [String: String]
    let digest: String; let settingSpecs: [SettingSpec]; let actions: [WindowAction]; let editable: Bool
}
/// settings.json 里数字与字符串混存，统一转成字符串给表单。
struct SettingValue: Decodable {
    let text: String
    init(from d: Decoder) throws {
        let c = try d.singleValueContainer()
        if let s = try? c.decode(String.self) { text = s }
        else if let i = try? c.decode(Int.self) { text = String(i) }
        else { text = String(try c.decode(Double.self)) }
    }
}
struct WindowResponse: Decodable { let window: WindowSnapshot }
