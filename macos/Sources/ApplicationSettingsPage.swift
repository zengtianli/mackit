import AppKit
import SwiftUI

struct ApplicationLanguage: Decodable, Identifiable { let id: String; let label: String }
struct ApplicationRow: Decodable, Identifiable {
    let id: String; let name: String; let path: String
    let languages: [ApplicationLanguage]; let selected: String; let digest: String
    let running: Bool; let status: String; let office: Bool
    func matches(_ query: String) -> Bool {
        query.isEmpty || ([name, id, office ? "Office 办公 中文" : ""] + languages.map(\.label))
            .joined(separator: " ").localizedCaseInsensitiveContains(query)
    }
}
struct ApplicationSnapshot: Decodable {
    let apps: [ApplicationRow]; let copy: [String: String]; let problems: [String]
    let isolated: Bool; let latestTransaction: String
}
struct ApplicationResponse: Decodable { let applications: ApplicationSnapshot }

extension AppModel {
    func loadApplications() {
        run("读取应用语言设置…") {
            self.applications = try await self.client.call(["action":"applicationSnapshot"], as: ApplicationResponse.self).applications
        }
    }
    func setApplicationLanguages(_ changes: [[String: String]]) {
        guard !readOnly else { return }
        run("备份并保存应用语言…") {
            let result = try await self.client.call(["action":"applicationLanguage", "changes":changes], as: MessageResponse.self)
            self.message = result.message
            self.applications = try await self.client.call(["action":"applicationSnapshot"], as: ApplicationResponse.self).applications
        }
    }
    func officeInChinese() {
        let changes = (applications?.apps ?? []).filter(\.office).map {
            ["id":$0.id, "language":"zh-Hans", "digest":$0.digest]
        }
        setApplicationLanguages(changes)
    }
    func restoreApplicationLanguages() {
        guard !readOnly, let transaction = applications?.latestTransaction, !transaction.isEmpty else { return }
        run("恢复上次语言修改…") {
            let result = try await self.client.call(["action":"applicationRestore", "transaction":transaction], as: MessageResponse.self)
            self.message = result.message
            self.applications = try await self.client.call(["action":"applicationSnapshot"], as: ApplicationResponse.self).applications
        }
    }
}

struct ApplicationSettingsPage: View {
    @EnvironmentObject var model: AppModel
    let accent: Color
    @State private var query = ""
    @FocusState private var searchFocused: Bool
    private var rows: [ApplicationRow] { (model.applications?.apps ?? []).filter { $0.matches(query) } }
    private var office: [ApplicationRow] { (model.applications?.apps ?? []).filter(\.office) }
    private func copy(_ key: String, _ fallback: String) -> String { model.applications?.copy[key] ?? fallback }
    var body: some View {
        VStack(alignment:.leading, spacing:18) {
            VStack(alignment:.leading, spacing:8) {
                Text("06 / APPLICATIONS").font(.caption.monospaced().weight(.semibold)).foregroundStyle(accent)
                Text(copy("title", "把常用软件，设成顺手的语言。")).font(.system(size:29,weight:.bold))
                Text(copy("subtitle", "集中管理软件的界面语言。重新打开对应应用后生效。")).foregroundStyle(.secondary)
            }
            HStack(spacing:14) {
                VStack(alignment:.leading, spacing:5) {
                    Label("Office 常用设置", systemImage:"character.bubble").font(.headline)
                    Text("已找到 \(office.count) 个 Office 应用").font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Button("Office 一起改成简体中文", action:model.officeInChinese)
                    .buttonStyle(.borderedProminent).disabled(model.busy || model.readOnly || office.isEmpty)
            }.padding(18).background(accent.opacity(0.07), in:RoundedRectangle(cornerRadius:12))
            HStack {
                TextField("搜索软件，例如：Office、Word、中文", text:$query)
                    .textFieldStyle(.roundedBorder).focused($searchFocused).accessibilityIdentifier("application-search")
                Button("重新读取", action:model.loadApplications).disabled(model.busy)
            }
            HStack {
                Text("\(rows.count) 个应用").font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button("恢复上次语言修改", action:model.restoreApplicationLanguages)
                    .disabled(model.busy || model.readOnly || (model.applications?.latestTransaction.isEmpty ?? true))
            }
            if model.applications == nil {
                Spacer(); HStack { Spacer(); ProgressView("读取应用设置…"); Spacer() }; Spacer()
            } else {
                ScrollView {
                    LazyVStack(spacing:10) {
                        ForEach(rows) { row in
                            HStack(alignment:.center, spacing:14) {
                                Image(nsImage:NSWorkspace.shared.icon(forFile:row.path)).resizable().frame(width:36,height:36).accessibilityHidden(true)
                                VStack(alignment:.leading, spacing:5) {
                                    Text(row.name).font(.headline)
                                    Label(row.status, systemImage:row.running ? "clock" : row.selected == "system" ? "globe" : "checkmark.circle.fill")
                                        .font(.caption).foregroundStyle(row.running ? Color.orange : row.selected == "system" ? Color.secondary : accent)
                                }.frame(maxWidth:.infinity,alignment:.leading)
                                Picker("\(row.name) 的界面语言", selection:Binding(get:{ row.selected }, set:{ language in
                                    model.setApplicationLanguages([["id":row.id, "language":language, "digest":row.digest]])
                                })) {
                                    ForEach(row.languages) { language in Text(language.label).tag(language.id) }
                                }.labelsHidden().frame(width:200).disabled(model.busy || model.readOnly || row.languages.count < 2)
                                    .help(row.languages.count < 2 ? copy("unavailable", "未声明可切换的语言") : "选择后保存，重新打开应用时生效")
                            }.padding(16).background(.background, in:RoundedRectangle(cornerRadius:12))
                        }
                        if rows.isEmpty { ContentUnavailableView.search(text:query).padding(.top,25) }
                    }
                }
            }
            if let problems = model.applications?.problems, !problems.isEmpty {
                DisclosureGroup("\(problems.count) 个应用未能读取") {
                    ScrollView { Text(problems.joined(separator:"\n")).font(.caption).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading) }.frame(maxHeight:100)
                }.font(.caption).foregroundStyle(.secondary)
            }
            Text(copy("footnote", "修改会保留恢复记录；重新打开对应应用后生效。")).font(.caption).foregroundStyle(.secondary)
        }.padding(28).background(Color(nsColor:.windowBackgroundColor))
        .task {
            for _ in 0..<600 {
                if Task.isCancelled { return }
                if !model.busy { if model.applications == nil { model.loadApplications() }; return }
                try? await Task.sleep(for:.milliseconds(50))
            }
        }
        .onReceive(NotificationCenter.default.publisher(for:Notification.Name("MacKitFind"))) { _ in searchFocused = true }
    }
}
