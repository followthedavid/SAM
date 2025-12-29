import AppIntents
import Foundation

/// Siri Shortcuts for SAM
/// "Hey Siri, ask SAM..."
/// "Hey Siri, tell SAM to flirt"
/// "Hey Siri, what's SAM's mood?"

// MARK: - Chat with SAM

struct AskSAMIntent: AppIntent {
    static var title: LocalizedStringResource = "Ask SAM"
    static var description = IntentDescription("Send a message to SAM and get a response")
    static var openAppWhenRun: Bool = false

    @Parameter(title: "Message")
    var message: String

    func perform() async throws -> some IntentResult & ReturnsValue<String> & ProvidesDialog {
        // Connect to SAM service
        let response = await SAMShortcutService.shared.sendMessage(message)
        return .result(value: response, dialog: IntentDialog(response))
    }
}

// MARK: - Set Mood

struct SetSAMMoodIntent: AppIntent {
    static var title: LocalizedStringResource = "Set SAM Mood"
    static var description = IntentDescription("Change SAM's current mood")

    @Parameter(title: "Mood")
    var mood: SAMMoodEntity

    func perform() async throws -> some IntentResult & ProvidesDialog {
        await SAMShortcutService.shared.setMood(mood.id)
        return .result(dialog: "SAM is now feeling \(mood.name)")
    }
}

struct SAMMoodEntity: AppEntity {
    var id: String
    var name: String

    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Mood"
    static var defaultQuery = SAMMoodQuery()

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: LocalizedStringResource(stringLiteral: name))
    }

    static let moods: [SAMMoodEntity] = [
        SAMMoodEntity(id: "neutral", name: "Neutral"),
        SAMMoodEntity(id: "happy", name: "Happy"),
        SAMMoodEntity(id: "playful", name: "Playful"),
        SAMMoodEntity(id: "flirty", name: "Flirty"),
        SAMMoodEntity(id: "focused", name: "Focused"),
        SAMMoodEntity(id: "aroused", name: "Aroused")
    ]
}

struct SAMMoodQuery: EntityQuery {
    func entities(for identifiers: [String]) async throws -> [SAMMoodEntity] {
        SAMMoodEntity.moods.filter { identifiers.contains($0.id) }
    }

    func suggestedEntities() async throws -> [SAMMoodEntity] {
        SAMMoodEntity.moods
    }
}

// MARK: - Trigger Animation

struct SAMAnimationIntent: AppIntent {
    static var title: LocalizedStringResource = "SAM Animation"
    static var description = IntentDescription("Make SAM perform an animation")

    @Parameter(title: "Animation")
    var animation: SAMAnimationEntity

    func perform() async throws -> some IntentResult & ProvidesDialog {
        await SAMShortcutService.shared.triggerAnimation(animation.id)
        return .result(dialog: "SAM is now doing: \(animation.name)")
    }
}

struct SAMAnimationEntity: AppEntity {
    var id: String
    var name: String

    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Animation"
    static var defaultQuery = SAMAnimationQuery()

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: LocalizedStringResource(stringLiteral: name))
    }

    static let animations: [SAMAnimationEntity] = [
        SAMAnimationEntity(id: "wave", name: "Wave"),
        SAMAnimationEntity(id: "flex", name: "Flex"),
        SAMAnimationEntity(id: "wink", name: "Wink"),
        SAMAnimationEntity(id: "stretch", name: "Stretch"),
        SAMAnimationEntity(id: "nod", name: "Nod"),
        SAMAnimationEntity(id: "flirt", name: "Flirt")
    ]
}

struct SAMAnimationQuery: EntityQuery {
    func entities(for identifiers: [String]) async throws -> [SAMAnimationEntity] {
        SAMAnimationEntity.animations.filter { identifiers.contains($0.id) }
    }

    func suggestedEntities() async throws -> [SAMAnimationEntity] {
        SAMAnimationEntity.animations
    }
}

// MARK: - Quick Flirt

struct FlirtWithSAMIntent: AppIntent {
    static var title: LocalizedStringResource = "Flirt with SAM"
    static var description = IntentDescription("Get a flirty response from SAM")
    static var openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult & ReturnsValue<String> & ProvidesDialog {
        let response = await SAMShortcutService.shared.quickFlirt()
        return .result(value: response, dialog: IntentDialog(response))
    }
}

// MARK: - Get Status

struct GetSAMStatusIntent: AppIntent {
    static var title: LocalizedStringResource = "SAM Status"
    static var description = IntentDescription("Get SAM's current status and mood")
    static var openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult & ReturnsValue<String> & ProvidesDialog {
        let status = await SAMShortcutService.shared.getStatus()
        return .result(value: status, dialog: IntentDialog(status))
    }
}

// MARK: - Shortcut Service

actor SAMShortcutService {
    static let shared = SAMShortcutService()

    private let serverURL = "http://localhost:8765" // REST endpoint for shortcuts

    func sendMessage(_ message: String) async -> String {
        // In production, this would make an HTTP request to the SAM service
        // For now, return a placeholder
        return "SAM says: I heard you say '\(message)'. Let me think about that..."
    }

    func setMood(_ mood: String) async {
        // Send mood change to service
        let defaults = UserDefaults(suiteName: "group.warpopen.atlas")
        defaults?.set(mood, forKey: "currentMood")
    }

    func triggerAnimation(_ animation: String) async {
        // Trigger animation via WebSocket or REST
    }

    func quickFlirt() async -> String {
        let flirts = [
            "Hey you... I've been thinking about you.",
            "*smirks* Miss me?",
            "You know, you're pretty cute when you ask me things.",
            "Mmm, I like when you talk to me like that.",
            "*winks* What else you want?"
        ]
        return flirts.randomElement() ?? "Hey there..."
    }

    func getStatus() async -> String {
        let defaults = UserDefaults(suiteName: "group.warpopen.atlas")
        let mood = defaults?.string(forKey: "currentMood") ?? "neutral"
        let connected = defaults?.bool(forKey: "isConnected") ?? false

        return "SAM is \(connected ? "online" : "offline") and feeling \(mood)."
    }
}

// MARK: - App Shortcuts Provider

struct SAMShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: AskSAMIntent(),
            phrases: [
                "Ask \(.applicationName) \(\.$message)",
                "Tell \(.applicationName) \(\.$message)",
                "Hey \(.applicationName) \(\.$message)"
            ],
            shortTitle: "Ask SAM",
            systemImageName: "bubble.left.fill"
        )

        AppShortcut(
            intent: FlirtWithSAMIntent(),
            phrases: [
                "Flirt with \(.applicationName)",
                "Make \(.applicationName) flirt",
                "\(.applicationName) say something flirty"
            ],
            shortTitle: "Flirt",
            systemImageName: "heart.fill"
        )

        AppShortcut(
            intent: GetSAMStatusIntent(),
            phrases: [
                "How is \(.applicationName)",
                "What's \(.applicationName)'s mood",
                "\(.applicationName) status"
            ],
            shortTitle: "Status",
            systemImageName: "person.fill.questionmark"
        )

        AppShortcut(
            intent: SetSAMMoodIntent(),
            phrases: [
                "Set \(.applicationName) mood to \(\.$mood)",
                "Make \(.applicationName) \(\.$mood)"
            ],
            shortTitle: "Set Mood",
            systemImageName: "face.smiling"
        )
    }
}
