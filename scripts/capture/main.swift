import AppKit
import SwiftUI

// Offscreen screenshot of the production MacKit window for the product page (scripts/capture-media.py).
// Built from macos/Sources (minus the App's own @main in UISelfTest.swift) plus this file, so the pixels come
// from the same ContentView/AppModel/WindowPage code as the release. The window is placed outside every display
// and may not become key or main; the app never activates and posts no input events. The window server still
// composites it (title bar, toolbar, sidebar material and selection, which an offscreen cacheDisplay cannot
// draw), and this process reads back only its own window's image.

/// A window AppKit is not allowed to move back onto a screen.
final class OffscreenWindow: NSWindow {
    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect { frameRect }
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

private typealias WindowImage = @convention(c) (CGRect, UInt32, UInt32, UInt32) -> Unmanaged<CGImage>?

@main enum CaptureMain {
    static func main() {
        MainActor.assumeIsolated {
            let app = NSApplication.shared
            app.setActivationPolicy(.accessory)
            Task { await run() }
            app.run()
        }
    }

    @MainActor static func run() async {
        var result: [String: Any] = [:]
        do {
            let args = CommandLine.arguments
            guard let i = args.firstIndex(of: "--out"), args.count > i + 1 else { throw EngineError.message("usage: --out <png>") }
            let out = URL(fileURLWithPath: args[i + 1])
            let title = Bundle.main.infoDictionary?["CFBundleDisplayName"] as? String ?? "MacKit"
            // Same scene size as MacKitApp's Window(...).defaultSize(width:1080,height:790).
            let frame = NSRect(x: -30000, y: -30000, width: 1080, height: 790)
            let window = OffscreenWindow(contentRect: frame, styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                                         backing: .buffered, defer: false)
            window.isReleasedWhenClosed = false
            window.title = title
            window.toolbarStyle = .unified
            window.appearance = NSAppearance(named: .aqua)
            // AppModel reads `-page` from the argument domain (the App's own verification channel); real HOME, read-only snapshot.
            let model = AppModel()
            let host = NSHostingView(rootView: ContentView().environmentObject(model))
            host.sceneBridgingOptions = .all
            window.contentView = host
            window.setFrame(frame, display: false)
            window.orderFrontRegardless()
            var ready = false
            for _ in 0..<1200 {
                try await Task.sleep(for: .milliseconds(100))
                if !model.error.isEmpty { throw EngineError.message(model.error) }
                if model.snapshot != nil && !model.busy && (model.page != .window || model.window != nil) { ready = true; break }
            }
            guard ready else { throw EngineError.message("The app state did not load within 120 s") }
            try await Task.sleep(for: .milliseconds(1500))  // let `-section` scroll and the list settle
            let onScreen = NSScreen.screens.contains { $0.frame.intersects(window.frame) }
            guard !onScreen, !window.isKeyWindow, !NSApp.isActive else { throw EngineError.message("Capture window was visible or active") }
            guard let core = dlopen("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics", RTLD_NOW),
                  let symbol = dlsym(core, "CGWindowListCreateImage") else { throw EngineError.message("CGWindowListCreateImage is unavailable") }
            let image = unsafeBitCast(symbol, to: WindowImage.self)
            // kCGWindowListOptionIncludingWindow; kCGWindowImageBoundsIgnoreFraming | kCGWindowImageBestResolution
            guard let shot = image(.null, 1 << 3, UInt32(window.windowNumber), (1 << 0) | (1 << 3))?.takeRetainedValue(),
                  let png = NSBitmapImageRep(cgImage: shot).representation(using: .png, properties: [:]) else {
                throw EngineError.message("The window image could not be read")
            }
            try png.write(to: out)
            result = ["ok": true, "file": out.path, "width": shot.width, "height": shot.height, "page": "\(model.page)",
                      "title": title, "window_frame": NSStringFromRect(window.frame), "on_screen": onScreen,
                      "key": window.isKeyWindow, "active": NSApp.isActive, "app_version": model.snapshot?.appVersion ?? ""]
            window.orderOut(nil)
        } catch { result = ["ok": false, "error": error.localizedDescription] }
        if let data = try? JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]) { print(String(decoding: data, as: UTF8.self)) }
        exit(result["ok"] as? Bool == true ? 0 : 1)
    }
}
