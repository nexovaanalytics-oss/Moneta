// SPDX-License-Identifier: EUPL-1.2
//
// Moneta Miner – Menüleisten-App für macOS 13+.
// Startet und stoppt XMRig über den launchd-Agent (moneta-miner.sh) und zeigt den Status der lokalen
// XMRig-API. Keine Abhängigkeiten; deploy/mac/install.sh baut die App lokal mit swiftc
// (Command Line Tools) und signiert sie ad hoc.

import AppKit
import SwiftUI

@main
struct MonetaMinerApp: App {
    @StateObject private var model = MinerModel()

    init() {
        // Nur eine Instanz (launchd-Agent und Doppelklick im Finder könnten sonst zwei starten)
        let me = NSRunningApplication.current
        if let id = me.bundleIdentifier,
           NSRunningApplication.runningApplications(withBundleIdentifier: id).contains(where: { $0 != me }) {
            exit(0)
        }
    }

    var body: some Scene {
        MenuBarExtra {
            MenuContent(model: model)
        } label: {
            Image(systemName: model.symbol)
        }
        .menuBarExtraStyle(.menu)
    }
}

struct MenuContent: View {
    @ObservedObject var model: MinerModel

    var body: some View {
        Text(model.statusLine)
        if let detail = model.detailLine {
            Text(detail)
        }
        if let error = model.lastError {
            Text("⚠︎ \(error)")
        }
        Divider()
        if model.running {
            Button("Miner stoppen") { model.control(["stop"]) }
                .disabled(model.busy)
        } else {
            Button("Miner starten") { model.control(["start"]) }
                .disabled(model.busy)
        }
        Picker("Threads", selection: Binding(
            get: { model.threads },
            set: { model.control(["threads", $0]) }
        )) {
            Text("Alle Kerne").tag("all")
            ForEach(Array(1...max(model.cpus, 1)), id: \.self) { n in
                Text("\(n)").tag(String(n))
            }
        }
        .disabled(model.busy)
        Toggle("Miner beim Anmelden starten", isOn: Binding(
            get: { model.autostart },
            set: { model.control(["autostart", $0 ? "on" : "off"]) }
        ))
        .disabled(model.busy)
        Divider()
        Button("Log öffnen") { model.openLog() }
        Button("Einstellungsordner öffnen") { model.openConfigFolder() }
        Divider()
        Button("Menü schließen (Miner läuft weiter)") { NSApp.terminate(nil) }
    }
}

final class MinerModel: ObservableObject {
    @Published var running = false
    @Published var autostart = false
    @Published var threads = "all"
    @Published var cpus = ProcessInfo.processInfo.activeProcessorCount
    @Published var hashrate: Double?
    @Published var paused = false
    @Published var pool: String?
    @Published var poolUp = false
    @Published var accepted = 0
    @Published var lastError: String?
    @Published var busy = false

    private let home = FileManager.default.homeDirectoryForCurrentUser
    private var ctl: URL { home.appendingPathComponent("Library/Application Support/Moneta/moneta-miner.sh") }
    private var confDir: URL { home.appendingPathComponent(".config/moneta") }
    private var logFile: URL { home.appendingPathComponent("Library/Logs/Moneta/xmrig.log") }
    private let apiPort = 18000
    private var timer: Timer?

    init() {
        refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
            self?.refresh()
        }
    }

    // MARK: Anzeige

    var symbol: String {
        if !running { return "bolt.slash" }
        if paused { return "pause.circle" }
        return "bolt.fill"
    }

    var statusLine: String {
        if busy { return "Moneta Miner – bitte warten …" }
        if !running { return "Miner gestoppt" }
        if paused { return "Miner pausiert (Akkubetrieb)" }
        if let h = hashrate { return "Miner läuft – \(Self.format(hashrate: h))" }
        return "Miner läuft – startet …"
    }

    var detailLine: String? {
        guard running else { return nil }
        guard let pool = pool else { return "XMRig-API nicht erreichbar" }
        return poolUp ? "Pool \(pool) verbunden · \(accepted) Shares" : "Pool \(pool) nicht verbunden"
    }

    static func format(hashrate h: Double) -> String {
        let f = NumberFormatter()
        f.locale = Locale.current
        f.minimumFractionDigits = h >= 1000 ? 2 : 0
        f.maximumFractionDigits = h >= 1000 ? 2 : 0
        if h >= 1000 { return "\(f.string(from: NSNumber(value: h / 1000)) ?? "?") kH/s" }
        return "\(f.string(from: NSNumber(value: h)) ?? "?") H/s"
    }

    // MARK: Aktionen

    func control(_ args: [String]) {
        busy = true
        lastError = nil
        DispatchQueue.global(qos: .userInitiated).async {
            let (code, output) = self.runCtl(args)
            DispatchQueue.main.async {
                self.busy = false
                if code != 0 {
                    self.lastError = output.split(separator: "\n").last.map(String.init) ?? "Fehler (\(code))"
                }
                self.refresh()
            }
        }
    }

    func openLog() {
        if FileManager.default.fileExists(atPath: logFile.path) {
            NSWorkspace.shared.open(logFile)
        } else {
            lastError = "Noch kein Log vorhanden"
        }
    }

    func openConfigFolder() {
        NSWorkspace.shared.open(confDir)
    }

    // MARK: Status

    func refresh() {
        DispatchQueue.global(qos: .utility).async {
            let (code, output) = self.runCtl(["status", "--plain"])
            var values: [String: String] = [:]
            for line in output.split(separator: "\n") {
                let parts = line.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                if parts.count == 2 { values[String(parts[0])] = String(parts[1]) }
            }
            DispatchQueue.main.async {
                if code != 0 {
                    self.running = false
                    self.lastError = output.split(separator: "\n").last.map(String.init)
                        ?? "moneta-miner.sh nicht gefunden – install.sh ausführen"
                    return
                }
                self.running = values["state"] == "running"
                self.autostart = values["autostart"] == "1"
                self.threads = values["threads"] ?? "all"
                if let c = values["cpus"].flatMap({ Int($0) }), c > 0 { self.cpus = c }
                if self.running {
                    self.fetchSummary()
                } else {
                    self.hashrate = nil
                    self.paused = false
                    self.pool = nil
                    self.poolUp = false
                }
            }
        }
    }

    private func fetchSummary() {
        guard let url = URL(string: "http://127.0.0.1:\(apiPort)/2/summary") else { return }
        var request = URLRequest(url: url, timeoutInterval: 3)
        let tokenFile = confDir.appendingPathComponent("xmrig-token")
        if let token = try? String(contentsOf: tokenFile, encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines), !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        URLSession.shared.dataTask(with: request) { data, response, _ in
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            let json = data.flatMap { try? JSONSerialization.jsonObject(with: $0) } as? [String: Any]
            DispatchQueue.main.async {
                guard status == 200, let json = json else {
                    self.hashrate = nil
                    self.pool = nil
                    self.poolUp = false
                    if status == 401 || status == 403 {
                        self.lastError = "XMRig-API lehnt das Token ab"
                    }
                    return
                }
                let totals = (json["hashrate"] as? [String: Any])?["total"] as? [Any] ?? []
                self.hashrate = totals.prefix(2).compactMap { ($0 as? NSNumber)?.doubleValue }.first { $0 > 0 }
                self.paused = json["paused"] as? Bool ?? false
                let connection = json["connection"] as? [String: Any] ?? [:]
                self.pool = connection["pool"] as? String
                self.poolUp = ((connection["uptime"] as? NSNumber)?.intValue ?? 0) > 0
                self.accepted = (connection["accepted"] as? NSNumber)?.intValue ?? 0
            }
        }.resume()
    }

    // MARK: Hilfsfunktionen

    private func runCtl(_ args: [String]) -> (Int32, String) {
        guard FileManager.default.isExecutableFile(atPath: ctl.path) else {
            return (127, "moneta-miner.sh nicht gefunden – install.sh ausführen")
        }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/bash")
        process.arguments = [ctl.path] + args
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        do {
            try process.run()
        } catch {
            return (126, error.localizedDescription)
        }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        return (process.terminationStatus, String(decoding: data, as: UTF8.self))
    }
}
