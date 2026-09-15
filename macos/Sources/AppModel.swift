import AppKit
import SwiftUI

@MainActor final class AppModel: ObservableObject {
    @Published var page: Page = .install
    @Published var snapshot: Snapshot?
    @Published var profile = "developer"
    @Published var selected = Set<String>()
    @Published var preview: Preview?
    @Published var dependencies: [Dependency] = []
    @Published var diagnosis: Diagnosis?
    @Published var busy = false
    @Published var activity = ""
    @Published var message = ""
    @Published var error = ""
    @Published var log = ""
    @Published var query = ""
    @Published var keyComponent = "all"
    @Published var showAdvanced = false
    @Published var fileID = "nvim-keys"
    @Published var file: FileResponse?
    @Published var editor = ""
    @Published var confirmInstall = false
    @Published var confirmRestore = false
    let client: EngineClient
    let demo: Bool
    init(home: String = NSHomeDirectory()) {
        client = EngineClient(home: home); demo = home != NSHomeDirectory()
    }
    var dirty: Bool { file != nil && editor != file?.content }
    var newest: Transaction? { snapshot?.transactions.first { ["applied", "installing"].contains($0.status) } }
    var filteredKeys: [KeyBinding] {
        (snapshot?.keys ?? []).filter {
            (showAdvanced || !$0.advanced || !query.isEmpty) && (keyComponent == "all" || $0.component == keyComponent)
            && ($0.profile == nil || $0.profile == profile)
            && (query.isEmpty || [$0.key, $0.description, $0.source, $0.component].joined(separator: " ").localizedCaseInsensitiveContains(query))
        }
    }
    func request(_ action: String) -> [String: Any] { ["action":action,"profile":profile,"components":selected.sorted()] }
    func invalidate() { preview = nil; dependencies = []; diagnosis = nil }
    func choose(_ name: String) {
        profile = name; selected = Set(snapshot?.profiles[name] ?? []); invalidate()
    }
    func run(_ label: String, _ body: @escaping @MainActor () async throws -> Void) {
        guard !busy else { return }
        busy = true; activity = label; error = ""; message = ""
        Task {
            defer { busy = false; activity = "" }
            do { try await body() } catch { self.error = error.localizedDescription }
        }
    }
    func refreshSnapshot(reset: Bool = false) async throws {
        let value = try await client.call(["action":"snapshot"], as: Snapshot.self)
        snapshot = value
        if reset { profile = value.profile; selected = Set(value.selected); invalidate() }
    }
    func refresh() {
        run("读取配置状态…") { try await self.refreshSnapshot(reset: true) }
    }
    func prepare() {
        run("准备并预览配置…") {
            let result = try await self.client.call(self.request("preview"), as: Preview.self)
            self.preview = result; self.dependencies = result.dependencies
            try await self.refreshSnapshot()
        }
    }
    func apply() {
        guard let preview else { return }
        var req = request("apply"); req["token"] = preview.token
        run("备份并安装配置…") {
            let result = try await self.client.call(req, as: MessageResponse.self)
            self.message = result.message; self.preview = nil
            try await self.refreshSnapshot(reset: true)
            let check = try await self.client.call(self.request("doctor"), as: DiagnosisResponse.self)
            self.diagnosis = check.diagnosis
        }
    }
    func installDependencies() {
        run("安装所选软件与依赖…") { [self] in
            self.log = ""
            let result = try await self.client.call(self.request("installDependencies"), as: MessageResponse.self) { [weak self] chunk in
                Task { @MainActor in
                    self?.log.append(chunk)
                    if let count = self?.log.count, count > 60000 { self?.log = String(self!.log.suffix(40000)) }
                }
            }
            self.message = result.message
            let check = try await self.client.call(self.request("dependencies"), as: DependenciesResponse.self)
            self.dependencies = check.dependencies
            try await self.refreshSnapshot()
        }
    }
    func check() {
        run("检查配置和依赖…") {
            let result = try await self.client.call(self.request("doctor"), as: DiagnosisResponse.self)
            self.diagnosis = result.diagnosis
            try await self.refreshSnapshot()
        }
    }
    func restore() {
        guard let newest else { return }
        run("恢复安装前的配置…") {
            let result = try await self.client.call(["action":"restore","transaction":newest.id], as: MessageResponse.self)
            self.message = result.message; self.diagnosis = nil
            try await self.refreshSnapshot(reset: true)
        }
    }
    func readFile() {
        run("读取配置文件…") {
            let value = try await self.client.call(["action":"readFile","file":self.fileID], as: FileResponse.self)
            self.file = value; self.editor = value.content
        }
    }
    func saveFile() {
        guard let file else { return }
        run("备份并保存文件…") {
            let value = try await self.client.call(["action":"saveFile","file":self.fileID,"content":self.editor,"digest":file.digest], as: FileResponse.self)
            self.file = value; self.editor = value.content; self.message = value.message ?? "已保存"
        }
    }
    func reveal(_ path: String) { NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath:path)]) }
    func open(_ url: String) { if let value = URL(string:url) { NSWorkspace.shared.open(value) } }
    func installHomebrew() {
        run("下载 Homebrew 官方安装包…") {
            if self.demo { throw EngineError.message("演示目录不会安装本机软件。") }
            let url = URL(string:"https://github.com/Homebrew/brew/releases/latest/download/Homebrew.pkg")!
            let (temp,response) = try await URLSession.shared.download(from:url)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw EngineError.message("下载未成功，请检查网络后重试，或打开 Homebrew 官网。") }
            let folder = FileManager.default.temporaryDirectory.appendingPathComponent("MacKit-Homebrew-\(UUID().uuidString)")
            try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
            let pkg = folder.appendingPathComponent("Homebrew.pkg")
            try FileManager.default.moveItem(at:temp,to:pkg)
            // The system Installer validates the signed package and asks for privileges.
            guard NSWorkspace.shared.open(pkg) else { throw EngineError.message("无法打开系统安装器，请从 Homebrew 官网安装。") }
            self.message = "在系统安装器完成 Homebrew 安装后，回到这里点“刷新”。管理员密码只在系统安装器输入。"
        }
    }
}
