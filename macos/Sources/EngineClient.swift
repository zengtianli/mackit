import Foundation

// Adapted from the local macapp scaffold's Process bridge: concurrent pipe drains,
// explicit GUI PATH and a structured error envelope. No external Python required.
enum EngineError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let value) = self { return value }; return nil }
}
private struct Probe: Decodable { let ok: Bool; let error: String? }
private final class Buffer: @unchecked Sendable { var value = Data() }

struct EngineClient: Sendable {
    let executable: URL
    let home: String

    init(home: String = NSHomeDirectory()) {
        self.home = home
        executable = Bundle.main.resourceURL!.appendingPathComponent("core/bin/mackit")
    }

    func call<T: Decodable>(_ request: [String: Any], as: T.Type,
        progress: (@Sendable (String) -> Void)? = nil) async throws -> T {
        let data = try JSONSerialization.data(withJSONObject: request)
        let output = try await execute(data, progress: progress)
        let decoder = JSONDecoder()
        let probe = try decoder.decode(Probe.self, from: output)
        guard probe.ok else { throw EngineError.message(probe.error ?? "操作未完成，请重试。") }
        do { return try decoder.decode(T.self, from: output) }
        catch { throw EngineError.message("无法读取配置结果：\(error.localizedDescription)") }
    }

    private func execute(_ input: Data, progress: (@Sendable (String) -> Void)?) async throws -> Data {
        let executable = executable, home = home
        return try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = executable
                process.arguments = ["--home", home, "gui"]
                var env = ProcessInfo.processInfo.environment
                env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:\(NSHomeDirectory())/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
                // Keep the Python freezer's private loader state out of brew's descendants.
                env.removeValue(forKey: "PYTHONHOME"); env.removeValue(forKey: "PYTHONPATH")
                process.environment = env
                let stdout = Pipe(), stderr = Pipe(), stdin = Pipe()
                process.standardOutput = stdout; process.standardError = stderr; process.standardInput = stdin
                let out = Buffer(), err = Buffer(), group = DispatchGroup()
                do { try process.run() }
                catch { continuation.resume(throwing: EngineError.message("无法启动内置配置工具：\(error.localizedDescription)")); return }
                group.enter()
                DispatchQueue.global().async { out.value = stdout.fileHandleForReading.readDataToEndOfFile(); group.leave() }
                group.enter()
                DispatchQueue.global().async {
                    while true {
                        let chunk = stderr.fileHandleForReading.availableData
                        if chunk.isEmpty { break }
                        err.value.append(chunk)
                        if err.value.count > 262144 { err.value = Data(err.value.suffix(131072)) }
                        progress?(String(decoding: chunk, as: UTF8.self))
                    }
                    group.leave()
                }
                do { try stdin.fileHandleForWriting.write(contentsOf: input); try stdin.fileHandleForWriting.close() }
                catch { try? stdin.fileHandleForWriting.close() }
                process.waitUntilExit(); group.wait()
                if process.terminationStatus != 0 {
                    continuation.resume(throwing: EngineError.message("配置工具未完成（\(process.terminationStatus)）：\(String(decoding: err.value.suffix(4000), as: UTF8.self))"))
                } else { continuation.resume(returning: out.value) }
            }
        }
    }
}
