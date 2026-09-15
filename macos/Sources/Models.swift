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
    case install = "安装配置", keys = "快捷键", files = "配置文件", health = "检查与恢复"
    var id: String { rawValue }
    var icon: String {
        switch self { case .install: "shippingbox"; case .keys: "command"; case .files: "doc.text"; case .health: "clock.arrow.circlepath" }
    }
}
