import SwiftUI

struct ContentView: View {
    @EnvironmentObject var model: AppModel
    @FocusState private var searchFocused: Bool
    private let accent = Color(red:0.20,green:0.40,blue:0.29)
    var body: some View {
        NavigationSplitView {
            VStack(alignment:.leading,spacing:18) {
                HStack(spacing:10) {
                    Image(systemName:"command").font(.system(size:30,weight:.bold)).foregroundStyle(accent)
                    VStack(alignment:.leading) { Text("MacKit").font(.title2.bold()); Text("你的 Mac 配置入口").font(.caption).foregroundStyle(.secondary) }
                }.padding(.horizontal,14).padding(.top,20)
                List(Page.allCases,selection:$model.page) { page in Label(page.rawValue,systemImage:page.icon).tag(page).padding(.vertical,6) }
                VStack(alignment:.leading,spacing:8) {
                    Label(model.snapshot?.installed == true ? "已连接现有配置" : "从这里配置新电脑",systemImage:model.snapshot?.installed == true ? "checkmark.circle.fill" : "sparkles").font(.caption)
                    Text("v\(model.snapshot?.appVersion ?? Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "") · macOS 原生应用").font(.caption2).foregroundStyle(.secondary)
                    if model.demo { Label("隔离演示目录",systemImage:"testtube.2").font(.caption).foregroundStyle(.orange) }
                }.padding(16)
            }.navigationSplitViewColumnWidth(min:190,ideal:215,max:250)
        } detail: {
            VStack(spacing:0) {
                if model.busy {
                    HStack { ProgressView().controlSize(.small); Text(model.activity); Spacer(); Text("请保持 App 打开").foregroundStyle(.secondary) }.font(.callout).padding(12).background(accent.opacity(0.08))
                }
                if !model.error.isEmpty { banner(model.error,icon:"exclamationmark.triangle.fill",color:.orange) }
                if !model.message.isEmpty { banner(model.message,icon:"checkmark.circle.fill",color:accent) }
                Group {
                    switch model.page { case .install: install; case .keys: keys; case .files: files; case .health: health }
                }.frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.topLeading)
            }.frame(minWidth:630)
        }
        .tint(accent)
        .toolbar {
            ToolbarItem { Button(action:model.refresh) { Label("刷新",systemImage:"arrow.clockwise") }.disabled(model.busy || model.dirty).keyboardShortcut("r") }
            ToolbarItem { Button { model.open("https://mackit.tianli.cyou/") } label: { Label("使用帮助",systemImage:"questionmark.circle") } }
        }
        .alert("备份并安装这些配置？",isPresented:$model.confirmInstall) {
            Button("取消",role:.cancel) { }
            Button("开始安装") { model.apply() }
        } message: { Text("将安装预览中列出的配置。已有文件会备份，个人覆盖保留。桌面功能需要对应应用与系统权限；此操作不自动开启系统服务。") }
        .alert("恢复最近一次安装前的配置？",isPresented:$model.confirmRestore) {
            Button("取消",role:.cancel) { }
            Button("恢复配置",role:.destructive) { model.restore() }
        } message: { Text("\(model.newest?.id ?? "")\n恢复最近一次仍有效的安装，保留软件本体与个人覆盖。若文件后来被其他程序替换，会先停止并提示。") }
        .onAppear { if model.snapshot == nil { model.refresh() } }
        .onReceive(NotificationCenter.default.publisher(for:Notification.Name("MacKitFind"))) { _ in model.page = .keys; searchFocused = true }
    }
    private func banner(_ text:String,icon:String,color:Color) -> some View {
        HStack(alignment:.top,spacing:10) { Image(systemName:icon).foregroundStyle(color); Text(text).textSelection(.enabled); Spacer() }.padding(12).frame(maxWidth:.infinity,alignment:.leading).background(color.opacity(0.08))
    }
    private func title(_ eyebrow:String,_ title:String,_ subtitle:String) -> some View {
        VStack(alignment:.leading,spacing:8) {
            Text(eyebrow).font(.caption.monospaced().weight(.semibold)).foregroundStyle(accent)
            Text(title).font(.system(size:29,weight:.bold))
            Text(subtitle).foregroundStyle(.secondary)
        }.padding(.bottom,10)
    }
    private func card<Content:View>(@ViewBuilder _ content:() -> Content) -> some View {
        VStack(alignment:.leading,spacing:14,content:content).padding(20).frame(maxWidth:.infinity,alignment:.leading)
            .background(.background,in:RoundedRectangle(cornerRadius:14)).overlay(RoundedRectangle(cornerRadius:14).stroke(.quaternary))
    }
    private var install: some View {
        ScrollView {
            VStack(alignment:.leading,spacing:20) {
                title("01 / SET UP","把常用工具，配置到位。","选择习惯与组件 → 预览变化 → 安装软件与配置。")
                card {
                    HStack {
                        Text("使用预设").font(.headline)
                        Picker("使用预设",selection:Binding(get:{model.profile},set:{model.choose($0)})) {
                            Text("Developer · 通用开发").tag("developer"); Text("Tianli · 个人习惯").tag("tianli")
                        }.labelsHidden().frame(maxWidth:310).disabled(model.busy || model.snapshot?.installed == true)
                        Spacer()
                    }
                    Text(model.profile == "tianli" ? "保留 S 保存、Q 退出、J/K 跳行与右侧修饰键等习惯。" : "保留 Neovim 原生移动与窗口键；默认安装终端工具。")
                        .font(.callout).foregroundStyle(.secondary)
                    if model.snapshot?.installed == true { Text("已安装的预设已锁定；切换前先在“检查与恢复”恢复当前安装。").font(.caption).foregroundStyle(.secondary) }
                    LazyVGrid(columns:[GridItem(.flexible()),GridItem(.flexible())],alignment:.leading,spacing:12) {
                        ForEach(model.snapshot?.components ?? []) { c in
                            Toggle(isOn:Binding(get:{model.selected.contains(c.id)},set:{ value in
                                if value { model.selected.insert(c.id) } else { model.selected.remove(c.id) }; model.invalidate()
                            })) {
                                VStack(alignment:.leading,spacing:2) { Text(c.id).font(.system(.body,design:.monospaced).weight(.medium)); Text(c.label).font(.caption).foregroundStyle(.secondary) }
                            }.disabled(model.busy)
                        }
                    }
                    HStack {
                        Button("预览配置变化",action:model.prepare).buttonStyle(.borderedProminent).controlSize(.large).disabled(model.busy || model.selected.isEmpty).keyboardShortcut(.return,modifiers:.command)
                        Text("预览会准备配置源，不修改现有应用配置。").font(.caption).foregroundStyle(.secondary)
                    }
                }
                if let preview = model.preview {
                    card {
                        Label("即将应用的配置",systemImage:"list.bullet.rectangle").font(.headline)
                        ForEach(preview.plan.entries) { e in
                            HStack(alignment:.top) { Text(e.component).font(.body.monospaced()).frame(width:95,alignment:.leading); Text(shortPath(e.target)).font(.caption.monospaced()).textSelection(.enabled); Spacer(); Text(e.label).font(.caption).foregroundStyle(e.action == "unchanged" ? .secondary : accent) }
                            Divider()
                        }
                        Text("另包含 MacKit 命令入口与预设记录；原文件与链接均保留备份。").font(.caption).foregroundStyle(.secondary)
                        Button("备份并安装配置") { model.confirmInstall = true }.buttonStyle(.borderedProminent).controlSize(.large).disabled(model.busy)
                    }
                    dependencyCard
                } else if model.snapshot?.brew.isEmpty == true {
                    card {
                        Label("首次安装软件需要 Homebrew",systemImage:"shippingbox").font(.headline)
                        Text("App 已自带运行环境。Homebrew 用来安装你选择的终端软件，系统安装器可能要求管理员密码。").foregroundStyle(.secondary)
                        Button("安装 Homebrew…",action:model.installHomebrew).disabled(model.busy || model.demo)
                    }
                }
                permissionCard
                if !model.log.isEmpty { logCard }
            }.padding(28)
        }.background(Color(nsColor:.windowBackgroundColor))
    }
    private var dependencyCard: some View {
        card {
            Label("软件与依赖",systemImage:"arrow.down.circle").font(.headline)
            LazyVGrid(columns:[GridItem(.flexible()),GridItem(.flexible()),GridItem(.flexible())],alignment:.leading,spacing:10) {
                ForEach(model.dependencies) { d in Label(d.label,systemImage:d.installed ? "checkmark.circle.fill" : "circle.dashed").font(.callout).foregroundStyle(d.installed ? accent : .secondary) }
            }
            if model.snapshot?.brew.isEmpty == true {
                Button("安装 Homebrew…",action:model.installHomebrew).disabled(model.busy || model.demo)
            } else {
                Button("安装缺失软件与依赖",action:model.installDependencies).disabled(model.busy || model.demo || !model.dependencies.contains { !$0.installed })
            }
            Text("按所选组件安装，不自动升级已有软件。遇到需要管理员授权的安装包，请使用系统安装器完成。Neovim 插件会在首次启动时联网下载。").font(.caption).foregroundStyle(.secondary)
            HStack { Link("Homebrew 官网",destination:URL(string:"https://brew.sh/")!); Link("Karabiner 安装器",destination:URL(string:"https://karabiner-elements.pqrs.org/")!) }.font(.caption)
        }
    }
    private var permissionCard: some View {
        card {
            Label("桌面权限，由你确认",systemImage:"hand.raised").font(.headline)
            Text("使用 Hammerspoon、Karabiner 或窗口管理时，按各应用提示开启辅助功能、输入监控等权限。MacKit 本身不需要监听键盘。").font(.callout).foregroundStyle(.secondary)
            HStack {
                Button("辅助功能设置") { model.open("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") }
                Button("输入监控设置") { model.open("x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent") }
            }.disabled(model.demo)
            if model.selected.contains("yabai") { Text("yabai/skhd 是可选高级组件；这里管理配置，不自动安装或启动服务。").font(.caption).foregroundStyle(.secondary) }
        }
    }
    private var keys: some View {
        VStack(alignment:.leading,spacing:14) {
            title("02 / FIND A KEY","忘了按什么？搜一下。","输入用途、按键或文件名，直接找到原生配置来源。")
            HStack {
                TextField("搜索，例如：编号、分屏、历史",text:$model.query).textFieldStyle(.roundedBorder).focused($searchFocused)
                Picker("组件",selection:$model.keyComponent) {
                    Text("全部组件").tag("all")
                    ForEach(model.snapshot?.components ?? []) { Text($0.id).tag($0.id) }
                }.frame(width:150)
            }
            HStack { Toggle("显示编码跳行",isOn:$model.showAdvanced); Spacer(); Text("\(model.filteredKeys.count) 条 · \(model.profile)").foregroundStyle(.secondary) }.font(.caption)
            HStack { Image(systemName:"lightbulb").foregroundStyle(accent); Text("行编号：V 选行 → 空格 n l → 01_、02_。leader = 空格，M = Option。").font(.callout) }
            ScrollView {
                LazyVStack(alignment:.leading,spacing:10) {
                    ForEach(model.filteredKeys) { key in
                        HStack(alignment:.top,spacing:16) {
                            Text(key.key).font(.system(.body,design:.monospaced).bold()).frame(width:150,alignment:.leading).textSelection(.enabled)
                            VStack(alignment:.leading,spacing:6) {
                                Text(key.description)
                                Text("\(key.component) · \(key.mode)").font(.caption).foregroundStyle(.secondary)
                                Button(key.source) { model.open("https://github.com/zengtianli/mackit/blob/main/"+key.source) }.buttonStyle(.link).font(.caption.monospaced())
                            }
                            Spacer(minLength:0)
                        }.padding(14).frame(maxWidth:.infinity,alignment:.leading).background(.background,in:RoundedRectangle(cornerRadius:10))
                    }
                    if model.filteredKeys.isEmpty { ContentUnavailableView.search(text:model.query) }
                }
            }
            Text("来自原生键位声明。插件内建键和其他应用抢键，需要在对应应用中检查。").font(.caption).foregroundStyle(.secondary)
        }.padding(28)
    }
    private var files: some View {
        VStack(alignment:.leading,spacing:14) {
            title("03 / CONFIGURE","配置文件，有固定位置。","在这里读取与编辑。每次保存前备份，并检查其他程序是否改过文件。")
            HStack {
                Picker("配置文件",selection:$model.fileID) { ForEach(model.snapshot?.files ?? []) { Text($0.id).tag($0.id) } }.disabled(model.busy || model.dirty)
                Button("读取文件",action:model.readFile).disabled(model.busy || model.dirty)
                if let file = model.file { Button("在 Finder 显示") { model.reveal(file.path) } }
            }
            if let file = model.file {
                Text(shortPath(file.path)).font(.caption.monospaced()).foregroundStyle(.secondary).textSelection(.enabled)
                TextEditor(text:$model.editor).font(.system(size:13,design:.monospaced)).border(Color.secondary.opacity(0.2)).disabled(model.busy)
                HStack {
                    Button("备份并保存",action:model.saveFile).buttonStyle(.borderedProminent).disabled(model.busy || !model.dirty).keyboardShortcut("s")
                    Button("放弃未保存修改") { model.editor = file.content }.disabled(model.busy || !model.dirty)
                    Text(model.dirty ? "有未保存修改" : "已与文件同步").font(.caption).foregroundStyle(.secondary)
                }
                Text("Hammerspoon 会监听配置变化；保存其文件可能立即重载。语法与插件设置请按对应应用要求修改。").font(.caption).foregroundStyle(.secondary)
            } else { ContentUnavailableView("选择一个配置文件",systemImage:"doc.text.magnifyingglass",description:Text("nvim-keys 是 Neovim 的统一键表；number 管理屏幕行号。")) }
        }.padding(28)
        .onChange(of:model.fileID) { _,_ in model.file = nil; model.editor = "" }
    }
    private var health: some View {
        ScrollView {
            VStack(alignment:.leading,spacing:20) {
                title("04 / KEEP IT WORKING","看清状态，也能退回。","检查配置来源和依赖，按安装记录恢复已有文件。")
                card {
                    HStack { Label("当前配置",systemImage:"checklist").font(.headline); Spacer(); Button("检查配置",action:model.check).disabled(model.busy) }
                    if let s = model.snapshot { Text(shortPath(s.sourceRoot)).font(.caption.monospaced()).textSelection(.enabled); Text("配置版本 \(s.sourceVersion) · \(s.profile)").foregroundStyle(.secondary) }
                    if let d = model.diagnosis {
                        Label(d.issues.isEmpty ? "配置来源与依赖检查通过" : "发现 \(d.issues.count) 项待处理",systemImage:d.issues.isEmpty ? "checkmark.circle.fill" : "exclamationmark.triangle").foregroundStyle(d.issues.isEmpty ? accent : .orange)
                        ForEach(d.issues,id:\.self) { Text($0).font(.callout.monospaced()).textSelection(.enabled) }
                        Text("此检查不代表所有插件已下载，也不能判断其他 App 是否抢键。").font(.caption).foregroundStyle(.secondary)
                    }
                }
                card {
                    HStack { Label("安装恢复记录",systemImage:"clock.arrow.circlepath").font(.headline); Spacer(); Button("恢复最近一次安装…") { model.confirmRestore = true }.disabled(model.busy || model.newest == nil) }
                    if model.snapshot?.transactions.isEmpty != false { Text("还没有需要恢复的安装记录。").foregroundStyle(.secondary) }
                    ForEach(model.snapshot?.transactions ?? []) { tx in
                        HStack { VStack(alignment:.leading) { Text(tx.id).font(.caption.monospaced()); Text("\(tx.profile) · \(tx.changed) 项变更").font(.caption).foregroundStyle(.secondary) }; Spacer(); Text(statusLabel(tx.status)).font(.caption) }; Divider()
                    }
                    Text("按从新到旧恢复；软件本体不会被卸载，个人覆盖保留。").font(.caption).foregroundStyle(.secondary)
                    Button("打开备份目录") { model.reveal(model.client.home+"/.local/state/mackit") }
                }
                if !model.log.isEmpty { logCard }
            }.padding(28)
        }
    }
    private var logCard: some View {
        card { DisclosureGroup("软件安装运行记录") { ScrollView { Text(model.log).font(.caption.monospaced()).frame(maxWidth:.infinity,alignment:.leading).textSelection(.enabled) }.frame(maxHeight:240) } }
    }
    private func shortPath(_ path:String) -> String { path.replacingOccurrences(of:model.client.home,with:"~") }
    private func statusLabel(_ status:String) -> String {
        ["applied":"已应用","restored":"已恢复","rolled_back":"失败后已回滚","installing":"安装未完成"][status] ?? status
    }
}
