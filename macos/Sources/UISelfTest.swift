import AppKit
import SwiftUI

@main enum MacKitMain {
    static func main() {
        guard CommandLine.arguments.contains("--ui-self-test") else { MacKitApp.main(); return }
        MainActor.assumeIsolated {
            let app = NSApplication.shared
            app.setActivationPolicy(.prohibited)
            Task { await UISelfTest.run() }
            app.run()
        }
    }
}

/// Runs the production views and action methods without presenting a window or input events.
@MainActor private final class UISelfTest: NSObject, NSWindowDelegate {
    var closed = false
    func windowWillClose(_ notification: Notification) { closed = true }

    static func run() async {
        var checks: [String: Bool] = [:]
        var images: [String] = []
        var imageStats: [String: [String: Int]] = [:]
        var failure = ""
        do {
            let args = CommandLine.arguments
            guard let index = args.firstIndex(of: "--demo-home"), args.count > index + 1,
                  let output = ProcessInfo.processInfo.environment["SOP_OUT_DIR"] else {
                throw EngineError.message("UI self-test requires --demo-home and SOP_OUT_DIR")
            }
            let home = URL(fileURLWithPath: args[index + 1]).standardizedFileURL
            // The runner creates a disposable home, never a real user configuration directory.
            guard home.lastPathComponent.hasPrefix("mackit-accept-"),
                  home.path != FileManager.default.homeDirectoryForCurrentUser.path else {
                throw EngineError.message("UI self-test requires an isolated temporary home")
            }
            let destination = URL(fileURLWithPath: output)
            try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
            let model = AppModel(home: home.path)
            model.refresh()
            try await idle(model)
            checks["refresh_real_engine"] = model.snapshot?.components.count == 14 && model.snapshot?.keys.isEmpty == false
            checks["initial_state"] = model.snapshot?.installed == false && model.preview == nil && !model.busy
            let developerSelection = Set(model.snapshot?.profiles["developer"] ?? [])
            model.choose("tianli")
            checks["profile_selection"] = model.profile == "tianli" && model.selected == Set(model.snapshot?.profiles["tianli"] ?? [])
            model.refresh()
            try await idle(model)
            checks["refresh_resets_selection"] = model.profile == "developer" && model.selected == developerSelection
            model.prepare()
            try await idle(model)
            checks["preview_action"] = model.preview?.plan.entries.isEmpty == false && model.snapshot?.installed == false
            checks["preview_isolated_source"] = model.snapshot?.sourceRoot.hasPrefix(home.path + "/") == true
            model.page = .keys
            let keyCount = model.filteredKeys.count
            model.keyComponent = "nvim"
            checks["component_filter"] = !model.filteredKeys.isEmpty && model.filteredKeys.count < keyCount && model.filteredKeys.allSatisfy { $0.component == "nvim" }
            model.query = "__no_such_mackit_key__"
            checks["empty_search"] = model.filteredKeys.isEmpty
            model.query = ""; model.keyComponent = "all"
            model.readFile()
            try await idle(model)
            checks["file_read"] = model.file?.content.isEmpty == false && !model.dirty
            model.editor += "\n-- unsaved self-test draft\n"
            checks["dirty_state"] = model.dirty
            model.editor = model.file?.content ?? ""
            checks["discard_draft"] = !model.dirty
            model.loadWindow()
            try await idle(model)
            checks["window_settings"] = model.window?.settingSpecs.isEmpty == false && !model.windowDirty
            let delegate = UISelfTest()
            let window = NSWindow(contentRect: NSRect(x: -20000, y: -20000, width: 1080, height: 790),
                                  styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
            window.isReleasedWhenClosed = false
            window.delegate = delegate
            window.appearance = NSAppearance(named: .aqua)
            window.contentView = NSHostingView(rootView: ContentView().environmentObject(model))
            for (name, page) in [("install", Page.install), ("keys", .keys), ("files", .files), ("health", .health), ("window", .window)] {
                model.page = page
                try await Task.sleep(for: .milliseconds(150))
                try await idle(model)
                let path = destination.appendingPathComponent("native-ui-\(name).png")
                let stats = try capture(window, path: path)
                checks["render_\(name)"] = (stats["bytes"] ?? 0) > 10000
                checks["render_dimensions_\(name)"] = (stats["width"] ?? 0) >= 1000 && (stats["height"] ?? 0) >= 700
                checks["render_opaque_\(name)"] = stats["transparent_pixels"] == 0 && stats["minimum_alpha"] == 255
                images.append(path.lastPathComponent)
                imageStats[path.lastPathComponent] = stats
            }
            checks["never_visible_or_key"] = !window.isVisible && !window.isKeyWindow && !NSApp.isActive
            let appDelegate = AppDelegate(); appDelegate.model = model
            checks["clean_quit_allowed"] = appDelegate.applicationShouldTerminate(NSApp) == .terminateNow
            window.performClose(nil)
            checks["close_action"] = delegate.closed && !window.isVisible
        } catch { failure = error.localizedDescription }
        let passed = failure.isEmpty && !checks.isEmpty && checks.values.allSatisfy { $0 }
        let result: [String: Any] = ["ok": passed, "checks": checks, "screenshots": images, "image_stats": imageStats, "error": failure,
            "scope": "Production SwiftUI views and AppModel actions with the real Python engine in a temporary home; five offscreen renders, refresh, selection, search, preview, file draft, window settings, close and clean quit. No input events, activation, installation or service changes."]
        if let data = try? JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]) {
            print(String(decoding: data, as: UTF8.self))
        }
        exit(passed ? 0 : 1)
    }

    private static func idle(_ model: AppModel) async throws {
        for _ in 0..<600 {
            if !model.busy {
                if !model.error.isEmpty { throw EngineError.message(model.error) }
                return
            }
            try await Task.sleep(for: .milliseconds(50))
        }
        throw EngineError.message("UI action timed out")
    }

    private static func capture(_ window: NSWindow, path: URL) throws -> [String: Int] {
        guard let view = window.contentView else { throw EngineError.message("No native content view") }
        view.layoutSubtreeIfNeeded(); view.displayIfNeeded()
        guard view.bounds.width >= 1000, view.bounds.height >= 700,
              let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) else {
            throw EngineError.message("Invalid native view dimensions")
        }
        view.cacheDisplay(in: view.bounds, to: bitmap)
        // Offscreen cacheDisplay omits the window compositor's opaque backing. Preserve
        // its real view pixels while supplying the light window background for the PNG.
        guard let source = bitmap.cgImage,
              let context = CGContext(data: nil, width: source.width, height: source.height,
                                      bitsPerComponent: 8, bytesPerRow: source.width * 4,
                                      space: CGColorSpaceCreateDeviceRGB(),
                                      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue) else {
            throw EngineError.message("Cannot create opaque screenshot context")
        }
        let rect = CGRect(x: 0, y: 0, width: source.width, height: source.height)
        context.setFillColor(CGColor(gray: 1, alpha: 1)); context.fill(rect)
        context.draw(source, in: rect)
        guard let pixels = context.data?.assumingMemoryBound(to: UInt8.self),
              let flattened = context.makeImage(),
              let png = NSBitmapImageRep(cgImage: flattened).representation(using: .png, properties: [:]) else {
            throw EngineError.message("PNG rendering failed")
        }
        var transparentPixels = 0, minimumAlpha = 255
        for y in 0..<source.height {
            for x in 0..<source.width {
                let alpha = Int(pixels[y * context.bytesPerRow + x * 4 + 3])
                minimumAlpha = min(minimumAlpha, alpha)
                if alpha != 255 { transparentPixels += 1 }
            }
        }
        try png.write(to: path)
        return ["bytes": png.count, "width": source.width, "height": source.height,
                "transparent_pixels": transparentPixels, "minimum_alpha": minimumAlpha]
    }
}
