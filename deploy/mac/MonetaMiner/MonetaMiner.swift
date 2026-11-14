// SPDX-License-Identifier: EUPL-1.2
//
// Moneta Miner – Menüleisten-App für macOS 13+.
// Startet und stoppt XMRig über den launchd-Agent (moneta-miner.sh) und zeigt den Betrieb dieses Macs:
// Hashrate in der Menüleiste, Verlauf der letzten Stunden, Zustand (läuft/pausiert/gestoppt), Hashrate je
// Thread, Pool-Verbindung und den Grund einer Pause (Akku/Ladelimit, Energiesparmodus, Wärme).
// Der Verlauf liegt nur im Speicher der App; den Verlauf über Tage zeigt das Ledger-Dashboard.
// Keine Abhängigkeiten; deploy/mac/install.sh baut die App lokal mit swiftc (Command Line Tools) und
// signiert sie ad hoc.

import AppKit
import IOKit.ps
import SwiftUI
#if canImport(Charts)
import Charts
#endif

@main
struct MonetaMinerApp: App {
    @StateObject private var model = MinerModel()
    @AppStorage("showRateInMenuBar") private var showRate = true

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
            CockpitView(model: model)
        } label: {
            HStack(spacing: 4) {
                Image(systemName: model.symbol)
                if showRate, let text = model.menuBarText {
                    Text(text)
                }
            }
        }
        .menuBarExtraStyle(.window)
    }
}

// MARK: - Datenmodell

enum MinerState: String {
    case mining = "läuft"
    case paused = "pausiert"
    case stopped = "gestoppt"
    case noData = "keine Daten"
}

/// Ein Messpunkt alle 10 s. rate = Hashrate (10-s-Mittel) in H/s, 0 bei Pause/Stopp.
struct Sample: Identifiable {
    let date: Date
    let rate: Double
    let state: MinerState
    var id: Date { date }
}

/// Zusammenhängender Zeitraum mit demselben Zustand (für die Zeitleiste).
struct Segment: Identifiable {
    let start: Date
    var end: Date
    let state: MinerState
    var id: Date { start }
}

/// Werte aus GET /2/summary der XMRig-API.
struct Summary {
    var rate10s: Double?
    var rate60s: Double?
    var rate15m: Double?
    var highest: Double?
    var paused = false
    var uptime = 0
    var pool: String?
    var poolUptime = 0
    var ping: Int?
    var accepted = 0
    var rejected = 0
    var version: String?

    init(json: [String: Any]) {
        let rates = (json["hashrate"] as? [String: Any])?["total"] as? [Any] ?? []
        func rate(_ i: Int) -> Double? {
            guard i < rates.count, let v = (rates[i] as? NSNumber)?.doubleValue, v > 0 else { return nil }
            return v
        }
        rate10s = rate(0)
        rate60s = rate(1)
        rate15m = rate(2)
        highest = ((json["hashrate"] as? [String: Any])?["highest"] as? NSNumber)?.doubleValue
        paused = json["paused"] as? Bool ?? false
        uptime = (json["uptime"] as? NSNumber)?.intValue ?? 0
        version = json["version"] as? String
        let connection = json["connection"] as? [String: Any] ?? [:]
        pool = connection["pool"] as? String
        poolUptime = (connection["uptime"] as? NSNumber)?.intValue ?? 0
        ping = (connection["ping"] as? NSNumber)?.intValue
        accepted = (connection["accepted"] as? NSNumber)?.intValue ?? 0
        rejected = (connection["rejected"] as? NSNumber)?.intValue ?? 0
    }

    /// aktuelle Hashrate: 10-s-Mittel, kurz nach dem Start das 60-s-Mittel
    var current: Double? { rate10s ?? rate60s }
}

/// Stromversorgung und Systemzustand dieses Macs (ohne Root-Rechte lesbar).
struct PowerInfo {
    var onBattery = false
    var adapterPresent = false
    var batteryPercent: Int?
    var charging = false
    var hasBattery = false
    var lowPowerMode = false
    var thermal: ProcessInfo.ThermalState = .nominal
    var chargeLimiter: String?

    /// Apps, die ein Ladelimit setzen und dazu das Netzteil logisch abschalten (Akku entlädt trotz Kabel)
    static let chargeLimiterNames = ["AlDente", "Battery Toolkit", "BatFi"]

    static func read() -> PowerInfo {
        var info = PowerInfo()
        if let blob = IOPSCopyPowerSourcesInfo()?.takeRetainedValue() {
            if let providing = IOPSGetProvidingPowerSourceType(blob)?.takeUnretainedValue() {
                info.onBattery = (providing as String) == "Battery Power"
            }
            let sources = (IOPSCopyPowerSourcesList(blob)?.takeRetainedValue() as? [AnyObject]) ?? []
            for source in sources {
                let raw = IOPSGetPowerSourceDescription(blob, source)?.takeUnretainedValue()
                guard let desc = raw as? [String: Any], desc["Type"] as? String == "InternalBattery" else { continue }
                info.hasBattery = true
                if let cur = (desc["Current Capacity"] as? NSNumber)?.intValue,
                   let capacity = (desc["Max Capacity"] as? NSNumber)?.intValue, capacity > 0 {
                    info.batteryPercent = cur * 100 / capacity
                }
                info.charging = desc["Is Charging"] as? Bool ?? false
            }
        }
        info.adapterPresent = IOPSCopyExternalPowerAdapterDetails()?.takeRetainedValue() != nil
        info.lowPowerMode = ProcessInfo.processInfo.isLowPowerModeEnabled
        info.thermal = ProcessInfo.processInfo.thermalState
        let appNames = NSWorkspace.shared.runningApplications.compactMap { $0.localizedName }
        info.chargeLimiter = chargeLimiterNames.first { tool in
            appNames.contains { $0.localizedCaseInsensitiveContains(tool) }
        }
        return info
    }

    var thermalText: String {
        switch thermal {
        case .nominal: return "normal"
        case .fair: return "erhöht"
        case .serious: return "hoch – macOS drosselt"
        case .critical: return "kritisch – macOS drosselt stark"
        @unknown default: return "unbekannt"
        }
    }

    var sourceText: String {
        guard hasBattery else { return "Netzteil" }
        var parts = [onBattery ? "Akku" : "Netzteil"]
        if let p = batteryPercent { parts.append("\(p) %") }
        if charging {
            parts.append("lädt")
        } else if onBattery {
            parts.append("entlädt")
        }
        if onBattery && adapterPresent { parts.append("Netzteil erkannt") }
        return parts.joined(separator: " · ")
    }
}

final class MinerModel: ObservableObject {
    @Published var running = false
    @Published var autostart = false
    @Published var threads = "all"
    @Published var cpus = ProcessInfo.processInfo.activeProcessorCount
    @Published var summary: Summary?
    @Published var threadRates: [Double] = []
    @Published var power = PowerInfo()
    @Published var samples: [Sample] = []
    @Published var lastError: String?
    @Published var busy = false

    static let interval: TimeInterval = 10                 // Abfrage der XMRig-API
    static let keep: TimeInterval = 6 * 3600               // Verlauf im Speicher

    private let home = FileManager.default.homeDirectoryForCurrentUser
    private var ctl: URL { home.appendingPathComponent("Library/Application Support/Moneta/moneta-miner.sh") }
    private var confDir: URL { home.appendingPathComponent(".config/moneta") }
    private var logFile: URL { home.appendingPathComponent("Library/Logs/Moneta/xmrig.log") }
    private let apiPort = 18000
    private var timer: Timer?
    private var refreshing = false
    private var statusFailed = false                       // lastError stammt aus refresh()

    init() {
        refresh()
        let t = Timer(timeInterval: MinerModel.interval, repeats: true) { [weak self] _ in self?.refresh() }
        RunLoop.main.add(t, forMode: .common)   // läuft auch, während das Fenster offen ist
        timer = t
    }

    // MARK: Anzeige

    var state: MinerState {
        if !running { return .stopped }
        guard let s = summary else { return .noData }
        if s.paused { return .paused }
        return (s.current ?? 0) > 0 ? .mining : .noData
    }

    var symbol: String {
        switch state {
        case .stopped: return "bolt.slash"
        case .paused: return "pause.circle"
        case .noData: return "hourglass"
        case .mining: return "bolt.fill"
        }
    }

    var menuBarText: String? {
        switch state {
        case .stopped: return nil
        case .paused: return "Pause"
        case .noData: return "…"
        case .mining: return summary?.current.map { MinerModel.format(hashrate: $0, digits: 1) }
        }
    }

    var statusLine: String {
        if busy { return "Bitte warten …" }
        switch state {
        case .stopped: return "Miner gestoppt"
        case .paused: return "Miner pausiert"
        case .noData: return summary == nil ? "Miner läuft – XMRig-API antwortet nicht" : "Miner läuft – startet …"
        case .mining: return "Miner läuft"
        }
    }

    /// Warum XMRig gerade nicht rechnet. Die XMRig-API meldet nur „paused“, den Grund ermittelt die App
    /// selbst aus der Stromversorgung (xmrig-start.sh startet XMRig mit --pause-on-battery).
    var pauseReason: String? {
        guard running, let s = summary else { return nil }
        if s.paused {
            if power.onBattery {
                var text = "Mac läuft auf Akku"
                if let p = power.batteryPercent { text += " (\(p) %)" }
                switch (power.adapterPresent, power.chargeLimiter) {
                case (true, let tool?):
                    text += ": Das Netzteil steckt, aber \(tool) lässt den Akku bis zur unteren Ladegrenze entladen."
                case (true, nil):
                    text += ", obwohl ein Netzteil erkannt wird – vermutlich ein Ladelimit."
                case (false, let tool?):
                    text += ". Falls das Netzteil steckt: \(tool) entlädt vermutlich bis zur unteren Ladegrenze."
                case (false, nil):
                    text += ", kein Netzteil."
                }
                return text + " XMRig pausiert im Akkubetrieb (--pause-on-battery)."
            }
            return "XMRig meldet eine Pause, Grund unbekannt – bitte das Log ansehen."
        }
        if s.pool != nil && s.poolUptime == 0 {
            return "Keine Verbindung zum Pool \(s.pool ?? "") – läuft P2Pool auf der NAS?"
        }
        return nil
    }

    /// Hinweise, die die Hashrate drücken, ohne XMRig anzuhalten.
    var hints: [String] {
        guard running else { return [] }
        var h: [String] = []
        if power.lowPowerMode {
            h.append("Energiesparmodus ist an – macOS bremst die Kerne, die Hashrate sinkt.")
        }
        if power.thermal == .serious || power.thermal == .critical {
            h.append("Wärmezustand \(power.thermalText).")
        }
        if let s = summary, s.rejected > 0 {
            h.append("\(s.rejected) Share(s) vom Pool abgelehnt – Log ansehen.")
        }
        return h
    }

    var dashboardURL: URL? {
        // eigene Adresse, sonst die vom Installer gekoppelte Ledger-Adresse
        for file in ["dashboard", "ledger"] {
            let url = confDir.appendingPathComponent(file)
            if let text = try? String(contentsOf: url, encoding: .utf8)
                .trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty {
                return URL(string: text)
            }
        }
        // Vorgabe: Dashboard auf demselben Host wie der Pool, Port 8090 (deploy/nas/compose.yaml)
        let poolFile = confDir.appendingPathComponent("pool")
        guard let pool = try? String(contentsOf: poolFile, encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines), !pool.isEmpty,
              let host = pool.split(separator: ":").first else { return nil }
        return URL(string: "http://\(host):8090")
    }

    static func format(hashrate h: Double, digits: Int = 2) -> String {
        let f = NumberFormatter()
        f.locale = Locale.current
        let kilo = h >= 1000
        f.minimumFractionDigits = kilo ? digits : 0
        f.maximumFractionDigits = kilo ? digits : 0
        if kilo { return "\(f.string(from: NSNumber(value: h / 1000)) ?? "?") kH/s" }
        return "\(f.string(from: NSNumber(value: h)) ?? "?") H/s"
    }

    static func format(duration seconds: Int) -> String {
        let s = max(seconds, 0)
        if s < 60 { return "\(s) s" }
        if s < 3600 { return "\(s / 60) min" }
        if s < 86400 { return "\(s / 3600) h \(s % 3600 / 60) min" }
        return "\(s / 86400) d \(s % 86400 / 3600) h"
    }

    // MARK: Verlauf

    func history(since start: Date) -> [Sample] {
        samples.filter { $0.date >= start }
    }

    func segments(since start: Date) -> [Segment] {
        let list = history(since: start)
        var result: [Segment] = []
        for (i, s) in list.enumerated() {
            let next = i + 1 < list.count ? list[i + 1].date : Date()
            // Lücken (Ruhezustand, App beendet) bleiben leer
            let end = min(next, s.date.addingTimeInterval(MinerModel.interval * 2))
            if let last = result.last, last.state == s.state, abs(last.end.timeIntervalSince(s.date)) < 1 {
                result[result.count - 1].end = end
            } else {
                result.append(Segment(start: s.date, end: end, state: s.state))
            }
        }
        return result
    }

    /// Kennzahlen für den gewählten Zeitraum: Ø-Hashrate beim Rechnen, Pausen- und Stoppzeit in Sekunden
    func stats(since start: Date) -> (average: Double?, paused: Int, stopped: Int) {
        let mining = history(since: start).filter { $0.state == .mining }
        let avg: Double? = mining.isEmpty ? nil : mining.map(\.rate).reduce(0, +) / Double(mining.count)
        var paused = 0.0
        var stopped = 0.0
        for seg in segments(since: start) {
            let d = seg.end.timeIntervalSince(seg.start)
            if seg.state == .paused { paused += d }
            if seg.state == .stopped { stopped += d }
        }
        return (avg, Int(paused), Int(stopped))
    }

    private func record() {
        let now = Date()
        let rate = state == .mining ? (summary?.current ?? 0) : 0
        samples.append(Sample(date: now, rate: rate, state: state))
        let cutoff = now.addingTimeInterval(-MinerModel.keep)
        if let first = samples.first, first.date < cutoff {
            samples.removeAll { $0.date < cutoff }
        }
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

    func openDashboard() {
        if let url = dashboardURL {
            NSWorkspace.shared.open(url)
        } else {
            lastError = "Dashboard-Adresse unbekannt – in ~/.config/moneta/dashboard eintragen"
        }
    }

    // MARK: Status

    func refresh() {
        guard !refreshing else { return }
        refreshing = true
        DispatchQueue.global(qos: .utility).async {
            let (code, output) = self.runCtl(["status", "--plain"])
            var values: [String: String] = [:]
            for line in output.split(separator: "\n") {
                let parts = line.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                if parts.count == 2 { values[String(parts[0])] = String(parts[1]) }
            }
            let running = code == 0 && values["state"] == "running"
            var summaryJSON: Any?
            var backendsJSON: Any?
            var httpStatus = 0
            if running {
                let group = DispatchGroup()
                group.enter()
                self.getJSON("/2/summary") { json, status in
                    summaryJSON = json
                    httpStatus = status
                    group.leave()
                }
                group.enter()
                self.getJSON("/2/backends") { json, _ in
                    backendsJSON = json
                    group.leave()
                }
                group.wait()
            }
            DispatchQueue.main.async {
                self.refreshing = false
                self.power = PowerInfo.read()
                if code != 0 {
                    self.running = false
                    self.summary = nil
                    self.threadRates = []
                    self.lastError = output.split(separator: "\n").last.map(String.init)
                        ?? "moneta-miner.sh status fehlgeschlagen (\(code))"
                    self.statusFailed = true
                    self.record()
                    return
                }
                if self.statusFailed {
                    self.statusFailed = false
                    self.lastError = nil
                }
                self.running = running
                self.autostart = values["autostart"] == "1"
                self.threads = values["threads"] ?? "all"
                if let c = values["cpus"].flatMap({ Int($0) }), c > 0 { self.cpus = c }
                if let json = summaryJSON as? [String: Any] {
                    self.summary = Summary(json: json)
                    if self.lastError == "XMRig-API lehnt das Token ab" { self.lastError = nil }
                } else {
                    self.summary = nil
                    if httpStatus == 401 || httpStatus == 403 {
                        self.lastError = "XMRig-API lehnt das Token ab"
                    }
                }
                self.threadRates = running ? MinerModel.parseThreadRates(backendsJSON) : []
                self.record()
            }
        }
    }

    /// Hashrate je CPU-Thread aus GET /2/backends (10-s-Mittel, sonst 60 s)
    static func parseThreadRates(_ json: Any?) -> [Double] {
        guard let backends = json as? [[String: Any]],
              let cpu = backends.first(where: { $0["type"] as? String == "cpu" }),
              let threads = cpu["threads"] as? [[String: Any]] else { return [] }
        return threads.map { t in
            let rates = t["hashrate"] as? [Any] ?? []
            for v in rates.prefix(2) {
                if let d = (v as? NSNumber)?.doubleValue, d > 0 { return d }
            }
            return 0
        }
    }

    private func getJSON(_ path: String, completion: @escaping (Any?, Int) -> Void) {
        guard let url = URL(string: "http://127.0.0.1:\(apiPort)\(path)") else {
            completion(nil, 0)
            return
        }
        var request = URLRequest(url: url, timeoutInterval: 3)
        let tokenFile = confDir.appendingPathComponent("xmrig-token")
        if let token = try? String(contentsOf: tokenFile, encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines), !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        URLSession.shared.dataTask(with: request) { data, response, _ in
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            let json = status == 200 ? data.flatMap { try? JSONSerialization.jsonObject(with: $0) } : nil
            completion(json, status)
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

// MARK: - Fenster

enum TimeWindow: Int, CaseIterable, Identifiable {
    case quarter = 900
    case hour = 3600
    case sixHours = 21600

    var id: Int { rawValue }
    var label: String {
        switch self {
        case .quarter: return "15 Min."
        case .hour: return "1 Std."
        case .sixHours: return "6 Std."
        }
    }
}

extension MinerState {
    var color: Color {
        switch self {
        case .mining: return .green
        case .paused: return .orange
        case .stopped: return .gray
        case .noData: return .red
        }
    }
}

struct CockpitView: View {
    @ObservedObject var model: MinerModel
    @AppStorage("showRateInMenuBar") private var showRate = true
    @AppStorage("chartWindow") private var windowRaw = TimeWindow.hour.rawValue

    private var window: TimeWindow { TimeWindow(rawValue: windowRaw) ?? .hour }

    var body: some View {
        let start = Date().addingTimeInterval(-Double(window.rawValue))
        VStack(alignment: .leading, spacing: 10) {
            header
            if let reason = model.pauseReason {
                Banner(text: reason, color: .orange, symbol: "pause.circle")
            }
            ForEach(model.hints, id: \.self) { hint in
                Banner(text: hint, color: .yellow, symbol: "exclamationmark.triangle")
            }
            if let error = model.lastError {
                Banner(text: error, color: .red, symbol: "xmark.octagon")
            }

            Divider()
            HStack {
                Text("Verlauf").font(.headline)
                Spacer()
                Picker("", selection: $windowRaw) {
                    ForEach(TimeWindow.allCases) { w in Text(w.label).tag(w.rawValue) }
                }
                .pickerStyle(.segmented)
                .labelsHidden()
                .frame(width: 190)
            }
            HistoryView(samples: model.history(since: start), segments: model.segments(since: start),
                        start: start, end: Date())
            statsLine(since: start)

            if !model.threadRates.isEmpty {
                Text("Hashrate je Thread").font(.headline)
                ThreadBars(rates: model.threadRates)
            }

            Divider()
            details

            Divider()
            controls
        }
        .padding(14)
        .frame(width: 360)
    }

    private var header: some View {
        HStack(alignment: .firstTextBaseline) {
            Circle().fill(model.state.color).frame(width: 10, height: 10)
            VStack(alignment: .leading, spacing: 2) {
                Text(model.statusLine).font(.headline)
                if let line = uptimeLine {
                    Text(line).font(.caption).foregroundColor(.secondary)
                }
            }
            Spacer()
            if model.state == .mining, let h = model.summary?.current {
                Text(MinerModel.format(hashrate: h))
                    .font(.system(size: 20, weight: .semibold, design: .rounded))
                    .monospacedDigit()
            }
        }
    }

    private var uptimeLine: String? {
        guard model.running, let s = model.summary else { return nil }
        var text = "seit \(MinerModel.format(duration: s.uptime))"
        if let v = s.version { text += " · XMRig \(v)" }
        return text
    }

    private func rateText(_ s: Summary) -> String {
        let values = [s.rate10s, s.rate60s, s.rate15m].map { rate -> String in
            guard let rate = rate else { return "–" }
            return MinerModel.format(hashrate: rate)
        }
        return values.joined(separator: " / ") + "  (10 s / 1 min / 15 min)"
    }

    private func statsLine(since start: Date) -> some View {
        let st = model.stats(since: start)
        var parts: [String] = []
        if let avg = st.average { parts.append("Ø \(MinerModel.format(hashrate: avg)) beim Rechnen") }
        parts.append("pausiert \(MinerModel.format(duration: st.paused))")
        if st.stopped > 0 { parts.append("gestoppt \(MinerModel.format(duration: st.stopped))") }
        return Text(parts.joined(separator: " · ")).font(.caption).foregroundColor(.secondary)
    }

    private var details: some View {
        let s = model.summary
        return Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 4) {
            if let s = s {
                row("Hashrate", rateText(s))
                if let h = s.highest, h > 0 { row("Höchstwert", MinerModel.format(hashrate: h)) }
                row("Pool", poolText(s))
                row("Shares", "\(s.accepted) angenommen · \(s.rejected) abgelehnt (Stratum, nicht Sidechain)")
            }
            row("Threads", threadsText)
            row("Strom", model.power.sourceText)
            row("Wärme", model.power.thermalText + (model.power.lowPowerMode ? " · Energiesparmodus an" : ""))
        }
        .font(.callout)
    }

    private var threadsText: String {
        let setting = model.threads == "all" ? "alle \(model.cpus) Kerne" : "\(model.threads) von \(model.cpus)"
        if model.threadRates.isEmpty { return "Einstellung: \(setting)" }
        return "\(model.threadRates.count) aktiv · Einstellung: \(setting)"
    }

    private func poolText(_ s: Summary) -> String {
        guard let pool = s.pool else { return "–" }
        guard s.poolUptime > 0 else { return "\(pool) · nicht verbunden" }
        var text = "\(pool) · seit \(MinerModel.format(duration: s.poolUptime))"
        if let ping = s.ping, ping > 0 { text += " · \(ping) ms" }
        return text
    }

    private func row(_ label: String, _ value: String) -> some View {
        GridRow {
            Text(label).foregroundColor(.secondary)
            Text(value).fixedSize(horizontal: false, vertical: true)
        }
    }

    private var controls: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                if model.running {
                    Button("Miner stoppen") { model.control(["stop"]) }
                } else {
                    Button("Miner starten") { model.control(["start"]) }
                        .keyboardShortcut(.defaultAction)
                }
                Spacer()
                Picker("Threads", selection: Binding(
                    get: { model.threads },
                    set: { model.control(["threads", $0]) }
                )) {
                    Text("Alle Kerne").tag("all")
                    ForEach(Array(1...max(model.cpus, 1)), id: \.self) { n in
                        Text("\(n)").tag(String(n))
                    }
                }
                .frame(width: 170)
            }
            .disabled(model.busy)
            Toggle("Miner beim Anmelden starten", isOn: Binding(
                get: { model.autostart },
                set: { model.control(["autostart", $0 ? "on" : "off"]) }
            ))
            .disabled(model.busy)
            Toggle("Hashrate in der Menüleiste zeigen", isOn: $showRate)
            HStack {
                Button("Dashboard") { model.openDashboard() }
                Button("Log") { model.openLog() }
                Button("Einstellungen") { model.openConfigFolder() }
                Spacer()
                Button("Beenden") { NSApp.terminate(nil) }
                    .help("Beendet nur die App – der Miner läuft weiter.")
            }
        }
    }
}

struct Banner: View {
    let text: String
    let color: Color
    let symbol: String

    var body: some View {
        HStack(alignment: .top, spacing: 6) {
            Image(systemName: symbol).foregroundColor(color)
            Text(text).font(.callout).fixedSize(horizontal: false, vertical: true)
        }
        .padding(8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 6).fill(color.opacity(0.12)))
    }
}

/// Hashrate-Verlauf (kH/s) und darunter eine Zeitleiste des Zustands.
struct HistoryView: View {
    let samples: [Sample]
    let segments: [Segment]
    let start: Date
    let end: Date

    var body: some View {
        if samples.count < 2 {
            Text("Der Verlauf füllt sich, solange die App läuft (alle \(Int(MinerModel.interval)) s ein Wert).")
                .font(.caption).foregroundColor(.secondary)
                .frame(maxWidth: .infinity, minHeight: 60)
        } else {
            VStack(alignment: .leading, spacing: 4) {
                rateChart.frame(height: 110)
                timeline.frame(height: 12)
                HStack(spacing: 10) {
                    ForEach([MinerState.mining, .paused, .stopped, .noData], id: \.self) { st in
                        HStack(spacing: 3) {
                            RoundedRectangle(cornerRadius: 2).fill(st.color).frame(width: 8, height: 8)
                            Text(st.rawValue)
                        }
                    }
                }
                .font(.caption2).foregroundColor(.secondary)
            }
        }
    }

    #if canImport(Charts)
    private var rateChart: some View {
        Chart(samples) { s in
            AreaMark(x: .value("Zeit", s.date), y: .value("kH/s", s.rate / 1000))
                .foregroundStyle(Color.accentColor.opacity(0.15))
            LineMark(x: .value("Zeit", s.date), y: .value("kH/s", s.rate / 1000))
                .foregroundStyle(Color.accentColor)
        }
        .chartXScale(domain: start...end)
        .chartYAxisLabel("kH/s")
    }

    private var timeline: some View {
        Chart(segments) { seg in
            BarMark(xStart: .value("Von", seg.start), xEnd: .value("Bis", seg.end), y: .value("Zustand", "Zustand"))
                .foregroundStyle(seg.state.color)
        }
        .chartXScale(domain: start...end)
        .chartXAxis(.hidden)
        .chartYAxis(.hidden)
    }
    #else
    // Rückfall ohne Swift Charts: einfache Linie und Zeitleiste
    private var rateChart: some View {
        GeometryReader { geo in
            Path { p in
                let maxRate = max(samples.map(\.rate).max() ?? 0, 1)
                let span = max(end.timeIntervalSince(start), 1)
                for (i, s) in samples.enumerated() {
                    let x = geo.size.width * CGFloat(s.date.timeIntervalSince(start) / span)
                    let y = geo.size.height * (1 - CGFloat(s.rate / maxRate))
                    if i == 0 { p.move(to: CGPoint(x: x, y: y)) } else { p.addLine(to: CGPoint(x: x, y: y)) }
                }
            }
            .stroke(Color.accentColor, lineWidth: 1.5)
        }
    }

    private var timeline: some View {
        GeometryReader { geo in
            ZStack(alignment: .topLeading) {
                ForEach(segments) { seg in
                    Rectangle()
                        .fill(seg.state.color)
                        .frame(width: max(1, geo.size.width * CGFloat(seg.end.timeIntervalSince(seg.start)
                                                                       / max(end.timeIntervalSince(start), 1))))
                        .offset(x: geo.size.width * CGFloat(seg.start.timeIntervalSince(start)
                                                             / max(end.timeIntervalSince(start), 1)))
                }
            }
        }
    }
    #endif
}

/// Hashrate je Thread als Balken – zeigt z. B., ob Effizienzkerne deutlich weniger liefern.
struct ThreadBars: View {
    let rates: [Double]

    var body: some View {
        let maxRate = max(rates.max() ?? 0, 1)
        HStack(alignment: .bottom, spacing: 3) {
            ForEach(rates.indices, id: \.self) { i in
                VStack(spacing: 2) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.accentColor.opacity(0.75))
                        .frame(height: max(2, 40 * CGFloat(rates[i] / maxRate)))
                    Text("\(i + 1)").font(.system(size: 9)).foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                .help("Thread \(i + 1): \(MinerModel.format(hashrate: rates[i]))")
            }
        }
        .frame(height: 54, alignment: .bottom)
    }
}
