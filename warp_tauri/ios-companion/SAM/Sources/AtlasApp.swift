import SwiftUI
import WidgetKit

/// SAM iOS Companion App
/// Your AI companion on your wrist and in your pocket
@main
struct SAMApp: App {
    @StateObject private var atlasService = SAMService.shared
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(atlasService)
                .onAppear {
                    atlasService.connect()
                }
                .onChange(of: scenePhase) { phase in
                    switch phase {
                    case .active:
                        atlasService.connect()
                    case .background:
                        atlasService.enterBackground()
                    case .inactive:
                        break
                    @unknown default:
                        break
                    }
                }
        }
    }
}

// MARK: - SAM Service

class SAMService: ObservableObject {
    static let shared = SAMService()

    @Published var isConnected = false
    @Published var currentMood: Mood = .neutral
    @Published var lastMessage: String = ""
    @Published var isThinking = false
    @Published var arousalLevel: Float = 0

    private var webSocket: URLSessionWebSocketTask?
    private let session = URLSession(configuration: .default)
    private let serverURL = "ws://localhost:8765" // Will be configurable

    enum Mood: String, CaseIterable {
        case neutral, happy, playful, flirty, focused, aroused

        var emoji: String {
            switch self {
            case .neutral: return "😐"
            case .happy: return "😊"
            case .playful: return "😏"
            case .flirty: return "😈"
            case .focused: return "💻"
            case .aroused: return "🔥"
            }
        }

        var color: Color {
            switch self {
            case .neutral: return .gray
            case .happy: return .yellow
            case .playful: return .pink
            case .flirty: return .purple
            case .focused: return .blue
            case .aroused: return .red
            }
        }
    }

    // MARK: - Connection

    func connect() {
        guard let url = URL(string: serverURL) else { return }

        webSocket = session.webSocketTask(with: url)
        webSocket?.resume()

        isConnected = true
        listenForMessages()

        // Register as iOS client
        send([
            "type": "register",
            "client_type": "ios_companion",
            "capabilities": ["notifications", "siri", "widget", "watch"]
        ])
    }

    func disconnect() {
        webSocket?.cancel(with: .goingAway, reason: nil)
        webSocket = nil
        isConnected = false
    }

    func enterBackground() {
        // Keep connection alive for notifications
        // iOS will manage the socket lifecycle
    }

    // MARK: - Messaging

    func send(_ message: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: message),
              let string = String(data: data, encoding: .utf8) else { return }

        webSocket?.send(.string(string)) { error in
            if let error = error {
                print("[SAM iOS] Send error: \(error)")
            }
        }
    }

    private func listenForMessages() {
        webSocket?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self?.handleMessage(text)
                    }
                @unknown default:
                    break
                }
                // Continue listening
                self?.listenForMessages()

            case .failure(let error):
                print("[SAM iOS] Receive error: \(error)")
                DispatchQueue.main.async {
                    self?.isConnected = false
                }
            }
        }
    }

    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return }

        DispatchQueue.main.async { [weak self] in
            switch type {
            case "emotion":
                if let emotion = json["emotion"] as? String {
                    self?.currentMood = Mood(rawValue: emotion) ?? .neutral
                }

            case "message":
                if let content = json["content"] as? String {
                    self?.lastMessage = content
                }

            case "arousal":
                if let level = json["level"] as? Float {
                    self?.arousalLevel = level
                }

            case "thinking":
                self?.isThinking = true

            case "done_thinking":
                self?.isThinking = false

            default:
                break
            }
        }
    }

    // MARK: - Actions

    func sendMessage(_ text: String) {
        send([
            "type": "user_message",
            "content": text,
            "source": "ios"
        ])
    }

    func setMood(_ mood: Mood) {
        send([
            "type": "set_mood",
            "mood": mood.rawValue
        ])
        currentMood = mood
    }

    func triggerAnimation(_ name: String) {
        send([
            "type": "animation",
            "animation": name
        ])
    }

    func quickFlirt() {
        send(["type": "quick_action", "action": "flirt"])
    }
}

// MARK: - Content View

struct ContentView: View {
    @EnvironmentObject var atlas: SAMService
    @State private var messageInput = ""
    @State private var showingMoodPicker = false

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Status bar
                StatusBar()

                // Main content
                ScrollView {
                    VStack(spacing: 20) {
                        // Avatar preview (placeholder)
                        AvatarView()

                        // Quick actions
                        QuickActions()

                        // Recent message
                        if !atlas.lastMessage.isEmpty {
                            MessageBubble(text: atlas.lastMessage)
                        }
                    }
                    .padding()
                }

                // Input bar
                InputBar(text: $messageInput) {
                    atlas.sendMessage(messageInput)
                    messageInput = ""
                }
            }
            .navigationTitle("SAM")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showingMoodPicker = true
                    } label: {
                        Text(atlas.currentMood.emoji)
                            .font(.title2)
                    }
                }
            }
            .sheet(isPresented: $showingMoodPicker) {
                MoodPicker()
            }
        }
    }
}

// MARK: - Sub Views

struct StatusBar: View {
    @EnvironmentObject var atlas: SAMService

    var body: some View {
        HStack {
            Circle()
                .fill(atlas.isConnected ? Color.green : Color.red)
                .frame(width: 8, height: 8)

            Text(atlas.isConnected ? "Connected" : "Offline")
                .font(.caption)
                .foregroundColor(.secondary)

            Spacer()

            if atlas.isThinking {
                ProgressView()
                    .scaleEffect(0.7)
                Text("Thinking...")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(.systemBackground))
    }
}

struct AvatarView: View {
    @EnvironmentObject var atlas: SAMService

    var body: some View {
        ZStack {
            // Placeholder for MetaHuman avatar stream
            RoundedRectangle(cornerRadius: 20)
                .fill(
                    LinearGradient(
                        colors: [atlas.currentMood.color.opacity(0.3), .black],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .frame(height: 300)

            VStack {
                Text(atlas.currentMood.emoji)
                    .font(.system(size: 80))

                Text("SAM")
                    .font(.title)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
            }
        }
    }
}

struct QuickActions: View {
    @EnvironmentObject var atlas: SAMService

    var body: some View {
        LazyVGrid(columns: [
            GridItem(.flexible()),
            GridItem(.flexible()),
            GridItem(.flexible())
        ], spacing: 12) {
            QuickActionButton(icon: "hand.wave", label: "Wave") {
                atlas.triggerAnimation("wave")
            }

            QuickActionButton(icon: "heart.fill", label: "Flirt") {
                atlas.quickFlirt()
            }

            QuickActionButton(icon: "sparkles", label: "Flex") {
                atlas.triggerAnimation("flex")
            }

            QuickActionButton(icon: "moon.fill", label: "Sleep") {
                atlas.setMood(.neutral)
            }

            QuickActionButton(icon: "flame.fill", label: "Heat") {
                atlas.setMood(.aroused)
            }

            QuickActionButton(icon: "gamecontroller", label: "Play") {
                atlas.setMood(.playful)
            }
        }
    }
}

struct QuickActionButton: View {
    let icon: String
    let label: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.title2)
                Text(label)
                    .font(.caption)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .background(Color(.secondarySystemBackground))
            .cornerRadius(12)
        }
        .buttonStyle(.plain)
    }
}

struct MessageBubble: View {
    let text: String

    var body: some View {
        HStack {
            Text(text)
                .padding()
                .background(Color.blue.opacity(0.1))
                .cornerRadius(16)
            Spacer()
        }
    }
}

struct InputBar: View {
    @Binding var text: String
    let onSubmit: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            TextField("Message SAM...", text: $text)
                .textFieldStyle(.roundedBorder)
                .submitLabel(.send)
                .onSubmit(onSubmit)

            Button(action: onSubmit) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title)
                    .foregroundColor(.blue)
            }
            .disabled(text.isEmpty)
        }
        .padding()
        .background(Color(.systemBackground))
    }
}

struct MoodPicker: View {
    @EnvironmentObject var atlas: SAMService
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            List(SAMService.Mood.allCases, id: \.self) { mood in
                Button {
                    atlas.setMood(mood)
                    dismiss()
                } label: {
                    HStack {
                        Text(mood.emoji)
                            .font(.title)
                        Text(mood.rawValue.capitalized)
                        Spacer()
                        if atlas.currentMood == mood {
                            Image(systemName: "checkmark")
                                .foregroundColor(.blue)
                        }
                    }
                }
                .buttonStyle(.plain)
            }
            .navigationTitle("Set Mood")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(SAMService.shared)
}
