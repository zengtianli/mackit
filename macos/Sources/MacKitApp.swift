import AppKit
import SwiftUI

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    weak var model: AppModel?
    func applicationShouldTerminate(_ sender:NSApplication) -> NSApplication.TerminateReply {
        if model?.busy == true {
            let alert=NSAlert(); alert.messageText="操作进行中"; alert.informativeText="请等当前操作完成后再退出，避免中断安装或恢复。"; alert.addButton(withTitle:"继续等待"); alert.runModal()
            return .terminateCancel
        }
        if model?.dirty == true {
            let alert=NSAlert(); alert.messageText="配置还有未保存修改"; alert.informativeText="退出后将丢弃编辑器中的修改，磁盘上的配置不会改变。"; alert.addButton(withTitle:"返回编辑"); alert.addButton(withTitle:"放弃并退出")
            return alert.runModal() == .alertSecondButtonReturn ? .terminateNow : .terminateCancel
        }
        return .terminateNow
    }
}

@main struct MacKitApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var model: AppModel
    init() {
        let args=CommandLine.arguments
        let home: String
        if let i=args.firstIndex(of:"--demo-home"),args.count>i+1 { home=args[i+1] } else { home=NSHomeDirectory() }
        _model=StateObject(wrappedValue:AppModel(home:home))
    }
    var body: some Scene {
        Window("Tianli MacKit",id:"main") {
            ContentView().environmentObject(model).onAppear { delegate.model=model }
        }.defaultSize(width:1080,height:790).windowResizability(.contentMinSize)
        .commands {
            CommandGroup(replacing:.newItem) { }
            CommandMenu("MacKit") {
                ForEach(Array(Page.allCases.enumerated()),id:\.offset) { index,page in
                    Button(page.rawValue) { model.page=page }.keyboardShortcut(KeyEquivalent(Character(String(index+1))))
                }
                Divider()
                Button("搜索快捷键") { NotificationCenter.default.post(name:Notification.Name("MacKitFind"),object:nil) }.keyboardShortcut("f")
                Button("打开在线手册") { model.open("https://mackit.tianli.cyou/keys.html") }
            }
        }
    }
}
