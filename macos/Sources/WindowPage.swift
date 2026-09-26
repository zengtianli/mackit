import AppKit
import SwiftUI

/// 组合键规范化：与引擎 localkeys.normalize 同一口径（修饰键排序 + 主键小写）。
enum KeyCombo {
    static let mods: [String: String] = ["cmd":"cmd","command":"cmd","⌘":"cmd","ctrl":"ctrl","control":"ctrl","⌃":"ctrl",
        "alt":"alt","opt":"alt","option":"alt","⌥":"alt","shift":"shift","⇧":"shift","left-cmd":"cmd"]
    static let order = ["cmd","ctrl","alt","shift"]
    /// Carbon keyCode → 引擎使用的键名（US 布局，与 localkeys.KEYCODES 相同）。
    static let names: [UInt16: String] = [0:"a",11:"b",8:"c",2:"d",14:"e",3:"f",5:"g",4:"h",34:"i",38:"j",40:"k",37:"l",46:"m",45:"n",31:"o",
        35:"p",12:"q",15:"r",1:"s",17:"t",32:"u",9:"v",13:"w",7:"x",16:"y",6:"z",18:"1",19:"2",20:"3",21:"4",
        23:"5",22:"6",26:"7",28:"8",25:"9",29:"0",41:";",39:"'",43:",",47:".",44:"/",42:"\\",33:"[",30:"]",
        27:"-",24:"=",50:"`",48:"tab",49:"space",36:"return",51:"delete",123:"left",124:"right",
        125:"down",126:"up",122:"f1",120:"f2",99:"f3",118:"f4",96:"f5",97:"f6",98:"f7",100:"f8",101:"f9",109:"f10"]
    static func canonical(_ raw: String) -> String? {
        var text = raw.lowercased()
        for symbol in ["⌘","⌃","⌥","⇧"] { text = text.replacingOccurrences(of: symbol, with: symbol + "+") }
        // skhd 写法 "ctrl + shift - y" → 最后一个 " - " 前是修饰键
        if let range = text.range(of: " - ", options: .backwards) { text.replaceSubrange(range, with: "+") }
        let parts = text.replacingOccurrences(of: " ", with: "+").split(separator: "+").map(String.init).filter { !$0.isEmpty }
        guard parts.count >= 2, let last = parts.last else { return nil }
        var set = Set<String>()
        for m in parts.dropLast() {
            if m == "hyper" { set.formUnion(["cmd","ctrl","shift"]); continue }
            guard let v = mods[m] else { return nil }
            set.insert(v)
        }
        return (order.filter(set.contains) + [last]).joined(separator: "+")
    }
    static func display(_ canon: String) -> String {
        let symbols = ["cmd":"⌘","ctrl":"⌃","alt":"⌥","shift":"⇧"]
        let parts = canon.split(separator: "+").map(String.init)
        guard let last = parts.last else { return canon }
        return parts.dropLast().map { symbols[$0] ?? $0 }.joined() + (last.count == 1 ? last.uppercased() : last)
    }
    static func from(_ event: NSEvent) -> String? {
        guard let name = names[event.keyCode] else { return nil }
        let f = event.modifierFlags
        let m = [(f.contains(.command),"cmd"),(f.contains(.control),"ctrl"),(f.contains(.option),"alt"),(f.contains(.shift),"shift")].filter(\.0).map(\.1)
        guard !m.isEmpty else { return nil }
        return (m + [name]).joined(separator: "+")
    }
}

/// 点一下开始录制，按下组合键即写入；Esc 取消。只监听本 App 自己的按键事件。
struct KeyRecorder: View {
    @Binding var key: String
    @State private var recording = false
    @State private var monitor: Any?
    var body: some View {
        Button {
            recording ? stop() : start()
        } label: {
            Text(recording ? "按下组合键…（Esc 取消）" : (key.isEmpty ? "录制" : KeyCombo.display(key)))
                .font(.system(.body, design: .monospaced).weight(.semibold)).frame(minWidth: 120)
        }
        .buttonStyle(.bordered).tint(recording ? .orange : nil)
        .help("点一下后直接按下新的组合键")
        .onDisappear(perform: stop)
    }
    private func start() {
        recording = true
        monitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
            if event.keyCode == 53 { stop(); return nil }
            if let combo = KeyCombo.from(event) { key = combo; stop(); return nil }
            return nil
        }
    }
    private func stop() {
        recording = false
        if let monitor { NSEvent.removeMonitor(monitor) }
        monitor = nil
    }
}

struct WindowPage: View {
    @EnvironmentObject var model: AppModel
    let accent: Color
    private let groups: [(String, [String])] = [
        ("布局", ["layout","auto_balance","split_ratio","window_placement"]),
        ("间隙与边距", ["window_gap","top_padding","bottom_padding","left_padding","right_padding"]),
        ("鼠标", ["mouse_modifier","mouse_action1","mouse_action2","mouse_drop_action","focus_follows_mouse","mouse_follows_focus"]),
        ("外观（需要脚本附加组件）", ["window_shadow","window_opacity","active_window_opacity","normal_window_opacity"]),
    ]

    var body: some View {
        ScrollViewReader { proxy in
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("05 / WINDOWS").font(.caption.monospaced().weight(.semibold)).foregroundStyle(accent)
                    Text("窗口管理，不用记参数。").font(.system(size: 29, weight: .bold))
                    Text("yabai 负责摆放窗口，skhd 负责快捷键。在这里改，保存时重新生成 yabairc 与 skhdrc，旧文件先备份。").foregroundStyle(.secondary)
                }.padding(.bottom, 10)
                if let w = model.window {
                    statusCard(w)
                    settingsCard(w)
                    hotkeyCard(w).id("hotkeys")
                    rulesCard.id("rules")
                    saveBar(w).id("save")
                } else {
                    ContentUnavailableView("正在读取窗口设置", systemImage: "rectangle.split.2x2", description: Text("读取 settings.json、hotkeys.json 与运行状态。"))
                }
            }.padding(28)
        }
        // 验证通道：`-section hotkeys|rules|save` 读到数据后直接滚到该区块（生产路径上为空）。
        .onChange(of: model.window?.digest) { _, _ in
            if let target = UserDefaults.standard.string(forKey: "section") { proxy.scrollTo(target, anchor: .top) }
        }
        }
        .onAppear { if model.window == nil { model.loadWindow() } }
        // 进入本页时若其他操作在进行（如启动时读取配置状态），等它结束再读，避免请求被忙碌锁吞掉。
        .onChange(of: model.busy) { _, busy in if !busy && model.window == nil { model.loadWindow() } }
    }

    private func card<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 14, content: content).padding(20).frame(maxWidth: .infinity, alignment: .leading)
            .background(.background, in: RoundedRectangle(cornerRadius: 14)).overlay(RoundedRectangle(cornerRadius: 14).stroke(.quaternary))
    }

    private func statusCard(_ w: WindowSnapshot) -> some View {
        card {
            HStack { Label("运行状态", systemImage: "bolt.horizontal.circle").font(.headline); Spacer()
                Button { model.loadWindow() } label: { Label("重新读取", systemImage: "arrow.clockwise") }.disabled(model.busy || model.windowDirty) }
            ForEach([("yabai", "摆放窗口", w.yabai), ("skhd", "全局快捷键", w.skhd)], id: \.0) { name, role, s in
                HStack(spacing: 12) {
                    Image(systemName: s.running ? "checkmark.circle.fill" : "pause.circle").foregroundStyle(s.running ? accent : .secondary)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(name) · \(role)").font(.body.weight(.medium))
                        Text(s.installed ? "\(s.version) · \(s.running ? "运行中" : "未运行")" : "未安装：按官方说明用 Homebrew 安装").font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    if s.installed {
                        Button(s.running ? "停止" : "启动") { model.windowService(name, start: !s.running) }.disabled(model.busy || model.demo)
                    }
                }
            }
            Text("脚本附加组件在 macOS 27 beta 上会打坏菜单栏，默认不加载；「外观」一组设置在加载它之前不生效。Hammerspoon 里的 3 个 yabai 开关（⌘⌃⇧Y/G/M）照常保留。")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    private func settingsCard(_ w: WindowSnapshot) -> some View {
        card {
            Label("yabai 设置", systemImage: "slider.horizontal.3").font(.headline)
            Text("留空 = 不写入配置，沿用 yabai 默认值。右侧灰字是当前实际运行的值。").font(.caption).foregroundStyle(.secondary)
            ForEach(groups, id: \.0) { title, keys in
                Text(title).font(.subheadline.weight(.semibold)).padding(.top, 4)
                ForEach(keys.compactMap { k in w.settingSpecs.first { $0.key == k } }) { spec in settingRow(spec, live: w.live[spec.key]) }
            }
        }
    }

    private func settingRow(_ spec: SettingSpec, live: String?) -> some View {
        let binding = Binding(get: { model.windowDraft.settings[spec.key] ?? "" }, set: { model.windowDraft.settings[spec.key] = $0 })
        return HStack(alignment: .firstTextBaseline, spacing: 14) {
            VStack(alignment: .leading, spacing: 2) {
                Text(spec.label).font(.body)
                Text(spec.help).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }.frame(maxWidth: .infinity, alignment: .leading)
            Group {
                if spec.kind == "choice" {
                    Picker(spec.label, selection: binding) {
                        Text("沿用默认").tag("")
                        ForEach(spec.choices, id: \.self) { Text($0).tag($0) }
                    }.labelsHidden().frame(width: 150)
                } else {
                    TextField(spec.range.count == 2 ? "\(fmt(spec.range[0]))–\(fmt(spec.range[1]))" : "", text: binding)
                        .textFieldStyle(.roundedBorder).frame(width: 150).font(.body.monospaced())
                }
            }
            Text(live.map { "当前 \($0)" } ?? "未运行").font(.caption.monospaced()).foregroundStyle(.secondary).lineLimit(1).frame(width: 150, alignment: .leading)
        }.padding(.vertical, 2)
    }

    private func fmt(_ v: Double) -> String { v == v.rounded() ? String(Int(v)) : String(v) }

    private func hotkeyCard(_ w: WindowSnapshot) -> some View {
        card {
            HStack { Label("skhd 快捷键", systemImage: "keyboard").font(.headline); Spacer()
                Button { model.windowDraft.hotkeys.append(HotkeyRow(key: "", action: w.actions.first?.id ?? "")) } label: { Label("添加快捷键", systemImage: "plus") } }
            Text("点按键格重新录制；动作从列表里选，也可以选「自定义命令」。与其他工具的全局键冲突会在行下标出。").font(.caption).foregroundStyle(.secondary)
            ForEach($model.windowDraft.hotkeys) { $row in
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 10) {
                        KeyRecorder(key: $row.key)
                        Picker("动作", selection: $row.action) {
                            ForEach(w.actions) { Text($0.label).tag($0.id) }
                            Divider()
                            Text("自定义命令").tag("")
                        }.labelsHidden().frame(width: 220)
                        if row.action.isEmpty {
                            TextField("单行 shell 命令，例如 yabai -m window --focus west", text: $row.command).textFieldStyle(.roundedBorder).font(.caption.monospaced())
                        }
                        TextField("备注（可选）", text: $row.note).textFieldStyle(.roundedBorder).frame(maxWidth: 180)
                        Spacer(minLength: 0)
                        Button(role: .destructive) { model.windowDraft.hotkeys.removeAll { $0.id == row.id } } label: { Image(systemName: "trash") }
                            .buttonStyle(.borderless).help("删除这条快捷键")
                    }
                    let clash = model.conflicts(for: row.key)
                    let dup = model.windowDraft.hotkeys.filter { $0.key == row.key && !row.key.isEmpty }.count > 1
                    if dup { Label("与本页另一条快捷键重复", systemImage: "exclamationmark.triangle.fill").font(.caption).foregroundStyle(.orange) }
                    ForEach(clash) { c in
                        Label("与 \(c.component) 冲突：\(c.description)", systemImage: "exclamationmark.triangle.fill").font(.caption).foregroundStyle(.orange)
                    }
                }
                Divider()
            }
        }
    }

    private var rulesCard: some View {
        card {
            HStack { Label("应用规则", systemImage: "app.badge").font(.headline); Spacer()
                Button { model.windowDraft.rules.append(AppRule(app: "")) } label: { Label("添加规则", systemImage: "plus") } }
            Text("用应用显示名（如 System Settings）。不接管 = yabai 不摆放它；桌面 = 打开时送到第几个桌面（需要脚本附加组件）。").font(.caption).foregroundStyle(.secondary)
            if model.windowDraft.rules.isEmpty { Text("还没有规则。").foregroundStyle(.secondary) }
            ForEach($model.windowDraft.rules) { $rule in
                HStack(spacing: 10) {
                    TextField("应用名", text: $rule.app).textFieldStyle(.roundedBorder).frame(width: 200)
                    Picker("接管", selection: $rule.manage) { Text("接管不变").tag(""); Text("不接管").tag("off"); Text("接管").tag("on") }.labelsHidden().frame(width: 110)
                    Picker("置顶", selection: $rule.sticky) { Text("置顶不变").tag(""); Text("所有桌面可见").tag("on"); Text("不置顶").tag("off") }.labelsHidden().frame(width: 130)
                    Picker("桌面", selection: $rule.space) { Text("桌面不变").tag(0); ForEach(1...9, id: \.self) { Text("桌面 \($0)").tag($0) } }.labelsHidden().frame(width: 110)
                    Spacer(minLength: 0)
                    Button(role: .destructive) { model.windowDraft.rules.removeAll { $0.id == rule.id } } label: { Image(systemName: "trash") }.buttonStyle(.borderless)
                }
            }
        }
    }

    private func saveBar(_ w: WindowSnapshot) -> some View {
        card {
            HStack {
                Button("保存并立即生效") { model.saveWindow(applyNow: true) }.buttonStyle(.borderedProminent).controlSize(.large)
                    .disabled(model.busy || !model.windowDirty || !w.editable).keyboardShortcut("s")
                Button("只保存") { model.saveWindow(applyNow: false) }.controlSize(.large)
                    .disabled(model.busy || !model.windowDirty || !w.editable).keyboardShortcut("s", modifiers: [.command, .shift])
                Button("放弃修改") { model.windowDraft = model.windowSaved }.disabled(model.busy || !model.windowDirty)
                Spacer()
                Text(model.windowDirty ? "有未保存修改" : "与配置文件一致").font(.caption).foregroundStyle(.secondary)
            }
            Text(w.editable ? "⌘S 保存并生效 · ⇧⌘S 只保存（下次启动 yabai 时生效）。保存前会检查文件是否被别处改过。" : "请先在「安装配置」里安装 yabai 组件，再修改窗口设置。")
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}
