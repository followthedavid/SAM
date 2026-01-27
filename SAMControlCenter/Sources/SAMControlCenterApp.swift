import SwiftUI
import AppKit

@main
struct SAMControlCenterApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var samState = SAMState()

    init() {
        // Share state
        AppDelegate.samState = samState
    }

    var body: some Scene {
        // Menu Bar Icon (brain in top bar)
        MenuBarExtra {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "brain.fill")
                        .foregroundStyle(.cyan)
                    Text("SAM Control Center")
                        .fontWeight(.medium)
                }
                .padding(.bottom, 4)

                Divider()

                Button("Open Window") {
                    AppDelegate.shared?.openMainWindow()
                }

                Button("Quit") {
                    NSApp.terminate(nil)
                }
            }
            .padding(8)
        } label: {
            Image(systemName: "brain.fill")
        }
    }
}

@MainActor
class AppDelegate: NSObject, NSApplicationDelegate {
    static var shared: AppDelegate?
    static var samState: SAMState?
    var mainWindow: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        AppDelegate.shared = self
        // Make this a regular app (not accessory/background) so windows show
        NSApp.setActivationPolicy(.regular)
        // Create and show window immediately
        DispatchQueue.main.async {
            self.openMainWindow()
        }
    }

    func openMainWindow() {
        if mainWindow == nil {
            let contentView = ContentView()
                .environmentObject(AppDelegate.samState ?? SAMState())
                .frame(minWidth: 700, minHeight: 550)

            mainWindow = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 750, height: 600),
                styleMask: [.titled, .closable, .miniaturizable, .resizable],
                backing: .buffered,
                defer: false
            )
            mainWindow?.title = "SAM Control Center"
            mainWindow?.contentView = NSHostingView(rootView: contentView)
            mainWindow?.center()
        }
        mainWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        openMainWindow()
        return true
    }
}

// MARK: - Voice Models

struct VoiceInfo: Identifiable, Codable, Equatable {
    let id: String
    let name: String
    let language: String?
    let isCustom: Bool

    enum CodingKeys: String, CodingKey {
        case id, name, language
        case isCustom = "is_custom"
    }

    init(id: String, name: String, language: String? = nil, isCustom: Bool = false) {
        self.id = id
        self.name = name
        self.language = language
        self.isCustom = isCustom
    }
}

// MARK: - SAM State

@MainActor
class SAMState: ObservableObject {
    @Published var services: [SAMService] = []
    @Published var resources: ResourceStatus = ResourceStatus()
    @Published var isHealthy: Bool = true
    @Published var lastUpdate: Date = Date()

    // Approval Queue State
    @Published var pendingApprovals: [ApprovalItem] = []
    @Published var isLoadingApprovals: Bool = false
    @Published var approvalError: String? = nil

    // Voice State (Phase 6.1)
    @Published var voiceEnabled: Bool {
        didSet { UserDefaults.standard.set(voiceEnabled, forKey: "sam_voice_enabled") }
    }
    @Published var selectedVoice: String {
        didSet { UserDefaults.standard.set(selectedVoice, forKey: "sam_selected_voice") }
    }
    @Published var voiceSpeed: Double {
        didSet { UserDefaults.standard.set(voiceSpeed, forKey: "sam_voice_speed") }
    }
    @Published var voicePitch: Double {
        didSet { UserDefaults.standard.set(voicePitch, forKey: "sam_voice_pitch") }
    }
    @Published var availableVoices: [VoiceInfo] = []
    @Published var isSpeaking: Bool = false
    @Published var voiceAPIAvailable: Bool = false

    private var timer: Timer?
    private var approvalTimer: Timer?
    private var speakingTask: Process?

    init() {
        // Load voice settings from UserDefaults
        self.voiceEnabled = UserDefaults.standard.bool(forKey: "sam_voice_enabled")
        self.selectedVoice = UserDefaults.standard.string(forKey: "sam_selected_voice") ?? "dustin_steele"

        // Load speed with default
        let savedSpeed = UserDefaults.standard.double(forKey: "sam_voice_speed")
        self.voiceSpeed = savedSpeed == 0 ? 1.0 : savedSpeed

        // Load pitch with default
        let savedPitch = UserDefaults.standard.double(forKey: "sam_voice_pitch")
        self.voicePitch = savedPitch == 0 ? 1.0 : savedPitch

        loadServices()
        startMonitoring()
        startApprovalMonitoring()

        // Fetch available voices
        Task {
            await fetchVoices()
        }
    }

    func loadServices() {
        services = [
            SAMService(id: "sam_brain", name: "SAM Brain", icon: "brain.fill", priority: .critical),
            SAMService(id: "orchestrator", name: "Orchestrator", icon: "arrow.triangle.branch", priority: .critical),
            SAMService(id: "scrapers", name: "Scrapers", icon: "arrow.down.doc.fill", priority: .high),
            SAMService(id: "training", name: "Training", icon: "graduationcap.fill", priority: .medium),
            SAMService(id: "dashboard", name: "Dashboard", icon: "chart.bar.fill", priority: .low),
        ]
    }

    func startMonitoring() {
        timer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.refresh()
            }
        }
        refresh()
    }

    func refresh() {
        Task {
            await fetchStatus()
        }
    }

    func fetchStatus() async {
        // Read from daemon state file
        let stateURL = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".sam/daemon/state.json")

        guard let data = try? Data(contentsOf: stateURL),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }

        // Parse services
        if let servicesDict = json["services"] as? [String: [String: Any]] {
            for (id, info) in servicesDict {
                if let index = services.firstIndex(where: { $0.id == id }) {
                    services[index].status = ServiceStatus(rawValue: info["status"] as? String ?? "stopped") ?? .stopped
                    services[index].pid = info["pid"] as? Int
                }
            }
        }

        lastUpdate = Date()
        isHealthy = services.filter { $0.priority == .critical }.allSatisfy { $0.status == .running }
    }

    func startService(_ id: String) {
        runDaemonCommand("start \(id)")
    }

    func stopService(_ id: String) {
        runDaemonCommand("stop \(id)")
    }

    func startAll() {
        runDaemonCommand("start")
    }

    func stopAll() {
        runDaemonCommand("stop")
    }

    private func runDaemonCommand(_ cmd: String) {
        let script = """
        cd ~/ReverseLab/SAM/warp_tauri/sam_brain && python3 unified_daemon.py \(cmd)
        """
        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = ["-c", script]
        try? task.run()
    }

    // MARK: - Chat API

    func chat(_ message: String) async -> String {
        guard let url = URL(string: "http://localhost:8765/api/orchestrate") else {
            return "Error: Invalid API URL"
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30

        let body = ["message": message]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let response = json["response"] as? String {
                return response
            }
            return "SAM is not responding. Make sure sam_api.py is running on port 8765."
        } catch {
            return "Connection error: \(error.localizedDescription). Is SAM running?"
        }
    }

    func roleplay(character: String, message: String) async -> String {
        guard let url = URL(string: "http://localhost:8765/api/orchestrate") else {
            return "Error: Invalid API URL"
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30

        let roleplayMessage = "[\(character) roleplay] \(message)"
        let body = ["message": roleplayMessage]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let response = json["response"] as? String {
                return response
            }
            return "SAM is not responding."
        } catch {
            return "Connection error: \(error.localizedDescription)"
        }
    }

    func checkOrchestrator() async -> Bool {
        let socketPath = "/tmp/sam_multi_orchestrator.sock"
        return FileManager.default.fileExists(atPath: socketPath)
    }

    // MARK: - Project API

    func fetchCurrentProject() async -> (name: String, type: String?, status: String, icon: String)? {
        guard let url = URL(string: "http://localhost:8765/api/project/current") else {
            return nil
        }

        var request = URLRequest(url: url)
        request.timeoutInterval = 5

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let projectDict = json["project"] as? [String: Any] {
                return (
                    name: projectDict["name"] as? String ?? "Unknown",
                    type: projectDict["type"] as? String,
                    status: projectDict["status"] as? String ?? "unknown",
                    icon: projectDict["icon"] as? String ?? "folder.fill"
                )
            }
            return nil
        } catch {
            return nil
        }
    }

    // MARK: - Image Analysis API

    func analyzeImage(imageData: Data, prompt: String) async -> (response: String, analysis: String) {
        guard let url = URL(string: "http://localhost:8765/api/vision/analyze") else {
            return ("Error: Invalid API URL", "Failed to analyze image")
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 60  // Image analysis may take longer

        // Create multipart form data
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var bodyData = Data()

        // Add image data
        bodyData.append("--\(boundary)\r\n".data(using: .utf8)!)
        bodyData.append("Content-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\n".data(using: .utf8)!)
        bodyData.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        bodyData.append(imageData)
        bodyData.append("\r\n".data(using: .utf8)!)

        // Add prompt
        bodyData.append("--\(boundary)\r\n".data(using: .utf8)!)
        bodyData.append("Content-Disposition: form-data; name=\"prompt\"\r\n\r\n".data(using: .utf8)!)
        bodyData.append((prompt.isEmpty ? "Describe this image in detail." : prompt).data(using: .utf8)!)
        bodyData.append("\r\n".data(using: .utf8)!)

        // Close boundary
        bodyData.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = bodyData

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                let response = json["response"] as? String ?? ""
                let analysis = json["analysis"] as? String ?? json["description"] as? String ?? response
                return (response, analysis)
            }
            return ("SAM analyzed the image.", "Image received. Vision API not available.")
        } catch {
            return ("Connection error: \(error.localizedDescription)", "Failed to analyze image: \(error.localizedDescription)")
        }
    }

    // MARK: - Feedback API

    func submitFeedback(responseId: String, responseContent: String, rating: String, correction: String?) async {
        guard let url = URL(string: "http://localhost:8765/api/cognitive/feedback") else {
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 10

        var body: [String: Any] = [
            "response_id": responseId,
            "response_content": responseContent,
            "rating": rating,
            "timestamp": ISO8601DateFormatter().string(from: Date())
        ]

        if let correction = correction {
            body["correction"] = correction
        }

        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse {
                print("Feedback submitted: \(httpResponse.statusCode)")
            }
        } catch {
            print("Feedback submission error: \(error.localizedDescription)")
        }
    }

    // MARK: - Approval Queue API

    func startApprovalMonitoring() {
        approvalTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.fetchPendingApprovals()
            }
        }
        Task {
            await fetchPendingApprovals()
        }
    }

    func fetchPendingApprovals() async {
        guard let url = URL(string: "http://localhost:8765/api/approval/queue") else {
            approvalError = "Invalid API URL"
            return
        }

        isLoadingApprovals = true
        approvalError = nil

        var request = URLRequest(url: url)
        request.timeoutInterval = 10

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                approvalError = "Invalid response"
                isLoadingApprovals = false
                return
            }

            if httpResponse.statusCode == 200 {
                let decoder = JSONDecoder()
                decoder.dateDecodingStrategy = .iso8601

                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let itemsArray = json["items"] as? [[String: Any]] {
                    // Manual parsing for flexibility with API responses
                    var items: [ApprovalItem] = []
                    for itemDict in itemsArray {
                        if let item = parseApprovalItem(itemDict) {
                            items.append(item)
                        }
                    }
                    pendingApprovals = items

                    // Send notification for new dangerous items
                    checkForDangerousItems(items)
                } else {
                    // Try direct decode
                    struct ApprovalResponse: Codable {
                        let items: [ApprovalItem]
                    }
                    let approvalResponse = try decoder.decode(ApprovalResponse.self, from: data)
                    pendingApprovals = approvalResponse.items
                    checkForDangerousItems(approvalResponse.items)
                }
            } else {
                approvalError = "Server error: \(httpResponse.statusCode)"
            }
        } catch {
            approvalError = "Connection error: \(error.localizedDescription)"
        }

        isLoadingApprovals = false
    }

    private func parseApprovalItem(_ dict: [String: Any]) -> ApprovalItem? {
        guard let id = dict["id"] as? String,
              let command = dict["command"] as? String,
              let riskLevelStr = dict["risk_level"] as? String,
              let reasoning = dict["reasoning"] as? String,
              let expectedOutcome = dict["expected_outcome"] as? String,
              let createdAtStr = dict["created_at"] as? String,
              let expiresAtStr = dict["expires_at"] as? String else {
            return nil
        }

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        let createdAt = formatter.date(from: createdAtStr) ?? Date()
        let expiresAt = formatter.date(from: expiresAtStr) ?? Date().addingTimeInterval(300)
        let riskLevel = RiskLevel(rawValue: riskLevelStr.uppercased()) ?? .moderate

        return ApprovalItem(
            id: id,
            command: command,
            riskLevel: riskLevel,
            reasoning: reasoning,
            expectedOutcome: expectedOutcome,
            createdAt: createdAt,
            expiresAt: expiresAt,
            alternatives: dict["alternatives"] as? [String],
            context: dict["context"] as? String
        )
    }

    private func checkForDangerousItems(_ items: [ApprovalItem]) {
        let dangerousItems = items.filter { $0.riskLevel == .dangerous || $0.riskLevel == .blocked }
        if !dangerousItems.isEmpty {
            sendNotification(
                title: "SAM Requires Approval",
                body: "\(dangerousItems.count) dangerous action(s) pending review"
            )
        }
    }

    private func sendNotification(title: String, body: String) {
        let notification = NSUserNotification()
        notification.title = title
        notification.informativeText = body
        notification.soundName = NSUserNotificationDefaultSoundName
        NSUserNotificationCenter.default.deliver(notification)
    }

    func approveItem(id: String) async -> Bool {
        guard let url = URL(string: "http://localhost:8765/api/approval/approve/\(id)") else {
            return false
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 10

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                // Remove from local list immediately for responsiveness
                pendingApprovals.removeAll { $0.id == id }
                return true
            }
            return false
        } catch {
            print("Approval error: \(error.localizedDescription)")
            return false
        }
    }

    func rejectItem(id: String, reason: String?) async -> Bool {
        guard let url = URL(string: "http://localhost:8765/api/approval/reject/\(id)") else {
            return false
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 10

        if let reason = reason {
            let body = ["reason": reason]
            request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        }

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                // Remove from local list immediately for responsiveness
                pendingApprovals.removeAll { $0.id == id }
                return true
            }
            return false
        } catch {
            print("Rejection error: \(error.localizedDescription)")
            return false
        }
    }

    func bulkApprove(ids: [String]) async -> Int {
        var approvedCount = 0
        for id in ids {
            if await approveItem(id: id) {
                approvedCount += 1
            }
        }
        return approvedCount
    }

    func bulkReject(ids: [String], reason: String?) async -> Int {
        var rejectedCount = 0
        for id in ids {
            if await rejectItem(id: id, reason: reason) {
                rejectedCount += 1
            }
        }
        return rejectedCount
    }

    // MARK: - Voice API (Phase 6.1)

    func fetchVoices() async {
        guard let url = URL(string: "http://localhost:8765/api/voice/voices") else {
            loadFallbackVoices()
            return
        }

        var request = URLRequest(url: url)
        request.timeoutInterval = 5

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                loadFallbackVoices()
                return
            }

            voiceAPIAvailable = true

            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let voicesArray = json["voices"] as? [[String: Any]] {
                var voices: [VoiceInfo] = []
                for voiceDict in voicesArray {
                    if let id = voiceDict["id"] as? String,
                       let name = voiceDict["name"] as? String {
                        let voice = VoiceInfo(
                            id: id,
                            name: name,
                            language: voiceDict["language"] as? String,
                            isCustom: voiceDict["is_custom"] as? Bool ?? false
                        )
                        voices.append(voice)
                    }
                }
                availableVoices = voices

                // If selected voice not in list, default to first
                if !voices.contains(where: { $0.id == selectedVoice }) && !voices.isEmpty {
                    selectedVoice = voices[0].id
                }
            } else {
                loadFallbackVoices()
            }
        } catch {
            print("Voice API error: \(error.localizedDescription)")
            voiceAPIAvailable = false
            loadFallbackVoices()
        }
    }

    private func loadFallbackVoices() {
        // Load macOS system voices as fallback
        availableVoices = [
            VoiceInfo(id: "Alex", name: "Alex (System)", language: "en-US", isCustom: false),
            VoiceInfo(id: "Daniel", name: "Daniel (System)", language: "en-GB", isCustom: false),
            VoiceInfo(id: "Samantha", name: "Samantha (System)", language: "en-US", isCustom: false),
            VoiceInfo(id: "Fred", name: "Fred (System)", language: "en-US", isCustom: false),
        ]

        // Reset to system voice if API not available
        if !availableVoices.contains(where: { $0.id == selectedVoice }) {
            selectedVoice = "Alex"
        }
    }

    func speak(text: String) async {
        guard !text.isEmpty else { return }

        isSpeaking = true

        if voiceAPIAvailable {
            await speakWithAPI(text: text)
        } else {
            await speakWithSystemVoice(text: text)
        }
    }

    private func speakWithAPI(text: String) async {
        guard let url = URL(string: "http://localhost:8765/api/voice/speak") else {
            await speakWithSystemVoice(text: text)
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30

        let body: [String: Any] = [
            "text": text,
            "voice": selectedVoice,
            "speed": voiceSpeed,
            "pitch": voicePitch
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                // Fallback to system voice
                await speakWithSystemVoice(text: text)
                return
            }

            // Check if API returned audio or status
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                if let status = json["status"] as? String, status == "speaking" {
                    // API is handling playback, wait for completion
                    await waitForSpeechCompletion()
                }
            }
        } catch {
            print("Voice API speak error: \(error.localizedDescription)")
            await speakWithSystemVoice(text: text)
        }

        isSpeaking = false
    }

    private func waitForSpeechCompletion() async {
        // Poll status endpoint until speaking is complete
        while true {
            try? await Task.sleep(nanoseconds: 500_000_000)  // 0.5 seconds

            guard let url = URL(string: "http://localhost:8765/api/voice/status") else { break }

            do {
                let (data, _) = try await URLSession.shared.data(from: url)
                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let speaking = json["is_speaking"] as? Bool {
                    if !speaking { break }
                }
            } catch {
                break
            }
        }
    }

    private func speakWithSystemVoice(text: String) async {
        // Use macOS say command as fallback
        let rate = Int(150 * voiceSpeed)  // Default rate is ~150 words/minute

        let task = Process()
        task.launchPath = "/usr/bin/say"
        task.arguments = ["-v", selectedVoice, "-r", String(rate), text]

        speakingTask = task

        do {
            try task.run()
            task.waitUntilExit()
        } catch {
            print("System voice error: \(error.localizedDescription)")
        }

        speakingTask = nil
        isSpeaking = false
    }

    func stopSpeaking() async {
        if voiceAPIAvailable {
            await stopSpeakingAPI()
        }

        // Also stop any local process
        speakingTask?.terminate()
        speakingTask = nil
        isSpeaking = false
    }

    private func stopSpeakingAPI() async {
        guard let url = URL(string: "http://localhost:8765/api/voice/stop") else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 5

        do {
            let _ = try await URLSession.shared.data(for: request)
        } catch {
            print("Stop speaking API error: \(error.localizedDescription)")
        }
    }

    func getVoiceStatus() async -> (isSpeaking: Bool, currentText: String?) {
        guard voiceAPIAvailable,
              let url = URL(string: "http://localhost:8765/api/voice/status") else {
            return (isSpeaking, nil)
        }

        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                let speaking = json["is_speaking"] as? Bool ?? false
                let text = json["current_text"] as? String
                return (speaking, text)
            }
        } catch {
            // Ignore errors
        }

        return (isSpeaking, nil)
    }
}

// MARK: - Models

enum ServicePriority: String, Codable {
    case critical, high, medium, low
}

enum ServiceStatus: String, Codable {
    case running, stopped, paused, error
}

struct SAMService: Identifiable {
    let id: String
    let name: String
    let icon: String
    let priority: ServicePriority
    var status: ServiceStatus = .stopped
    var pid: Int?

    var statusColor: Color {
        switch status {
        case .running: return .green
        case .stopped: return .gray
        case .paused: return .orange
        case .error: return .red
        }
    }
}

struct ResourceStatus {
    var ramTotal: Double = 8.0
    var ramAvailable: Double = 2.0
    var cpuPercent: Double = 30.0

    var ramUsedPercent: Double {
        1.0 - (ramAvailable / ramTotal)
    }
}

// MARK: - Approval Queue Models

enum RiskLevel: String, Codable, CaseIterable {
    case safe = "SAFE"
    case moderate = "MODERATE"
    case dangerous = "DANGEROUS"
    case blocked = "BLOCKED"

    var color: Color {
        switch self {
        case .safe: return .green
        case .moderate: return .yellow
        case .dangerous: return .red
        case .blocked: return .black
        }
    }

    var displayName: String {
        rawValue.capitalized
    }
}

struct ApprovalItem: Identifiable, Codable {
    let id: String
    let command: String
    let riskLevel: RiskLevel
    let reasoning: String
    let expectedOutcome: String
    let createdAt: Date
    let expiresAt: Date
    let alternatives: [String]?
    let context: String?

    enum CodingKeys: String, CodingKey {
        case id
        case command
        case riskLevel = "risk_level"
        case reasoning
        case expectedOutcome = "expected_outcome"
        case createdAt = "created_at"
        case expiresAt = "expires_at"
        case alternatives
        case context
    }

    var timeRemaining: TimeInterval {
        expiresAt.timeIntervalSinceNow
    }

    var isExpired: Bool {
        timeRemaining <= 0
    }

    var timeRemainingFormatted: String {
        let remaining = max(0, timeRemaining)
        if remaining < 60 {
            return "\(Int(remaining))s"
        } else if remaining < 3600 {
            return "\(Int(remaining / 60))m"
        } else {
            return "\(Int(remaining / 3600))h"
        }
    }
}
