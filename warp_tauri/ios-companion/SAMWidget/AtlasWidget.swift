import WidgetKit
import SwiftUI

/// SAM Home Screen Widget
/// Quick access to your AI companion from the home screen

struct SAMWidgetEntry: TimelineEntry {
    let date: Date
    let mood: String
    let moodEmoji: String
    let lastMessage: String
    let isConnected: Bool
}

struct SAMWidgetProvider: TimelineProvider {
    func placeholder(in context: Context) -> SAMWidgetEntry {
        SAMWidgetEntry(
            date: Date(),
            mood: "neutral",
            moodEmoji: "😊",
            lastMessage: "Hey, what's up?",
            isConnected: true
        )
    }

    func getSnapshot(in context: Context, completion: @escaping (SAMWidgetEntry) -> Void) {
        let entry = SAMWidgetEntry(
            date: Date(),
            mood: UserDefaults(suiteName: "group.warpopen.atlas")?.string(forKey: "currentMood") ?? "neutral",
            moodEmoji: getMoodEmoji(UserDefaults(suiteName: "group.warpopen.atlas")?.string(forKey: "currentMood") ?? "neutral"),
            lastMessage: UserDefaults(suiteName: "group.warpopen.atlas")?.string(forKey: "lastMessage") ?? "Tap to chat...",
            isConnected: UserDefaults(suiteName: "group.warpopen.atlas")?.bool(forKey: "isConnected") ?? false
        )
        completion(entry)
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SAMWidgetEntry>) -> Void) {
        let defaults = UserDefaults(suiteName: "group.warpopen.atlas")

        let entry = SAMWidgetEntry(
            date: Date(),
            mood: defaults?.string(forKey: "currentMood") ?? "neutral",
            moodEmoji: getMoodEmoji(defaults?.string(forKey: "currentMood") ?? "neutral"),
            lastMessage: defaults?.string(forKey: "lastMessage") ?? "Tap to chat...",
            isConnected: defaults?.bool(forKey: "isConnected") ?? false
        )

        // Update every 15 minutes
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 15, to: Date())!
        let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
        completion(timeline)
    }

    private func getMoodEmoji(_ mood: String) -> String {
        switch mood {
        case "happy": return "😊"
        case "playful": return "😏"
        case "flirty": return "😈"
        case "focused": return "💻"
        case "aroused": return "🔥"
        default: return "😐"
        }
    }
}

// MARK: - Small Widget

struct SAMWidgetSmall: View {
    let entry: SAMWidgetEntry

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient(
                colors: [.purple.opacity(0.6), .blue.opacity(0.4)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(entry.moodEmoji)
                        .font(.title)
                    Spacer()
                    Circle()
                        .fill(entry.isConnected ? Color.green : Color.red)
                        .frame(width: 8, height: 8)
                }

                Spacer()

                Text("SAM")
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(.white)

                Text(entry.lastMessage)
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.8))
                    .lineLimit(2)
            }
            .padding()
        }
    }
}

// MARK: - Medium Widget

struct SAMWidgetMedium: View {
    let entry: SAMWidgetEntry

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [.purple.opacity(0.6), .blue.opacity(0.4)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            HStack(spacing: 16) {
                // Avatar placeholder
                ZStack {
                    Circle()
                        .fill(.white.opacity(0.2))
                        .frame(width: 80, height: 80)

                    Text(entry.moodEmoji)
                        .font(.system(size: 40))
                }

                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("SAM")
                            .font(.headline)
                            .fontWeight(.bold)
                            .foregroundColor(.white)

                        Circle()
                            .fill(entry.isConnected ? Color.green : Color.red)
                            .frame(width: 8, height: 8)
                    }

                    Text(entry.lastMessage)
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.9))
                        .lineLimit(2)

                    Text(entry.mood.capitalized)
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.6))
                }

                Spacer()
            }
            .padding()
        }
    }
}

// MARK: - Large Widget

struct SAMWidgetLarge: View {
    let entry: SAMWidgetEntry

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [.purple.opacity(0.6), .blue.opacity(0.4)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            VStack(spacing: 16) {
                // Header
                HStack {
                    Text("SAM")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)

                    Spacer()

                    HStack(spacing: 4) {
                        Circle()
                            .fill(entry.isConnected ? Color.green : Color.red)
                            .frame(width: 8, height: 8)
                        Text(entry.isConnected ? "Online" : "Offline")
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.7))
                    }
                }

                // Avatar
                ZStack {
                    Circle()
                        .fill(.white.opacity(0.15))
                        .frame(width: 100, height: 100)

                    Text(entry.moodEmoji)
                        .font(.system(size: 50))
                }

                // Message
                Text(entry.lastMessage)
                    .font(.body)
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)
                    .lineLimit(3)

                Spacer()

                // Quick actions
                HStack(spacing: 20) {
                    QuickActionWidget(icon: "hand.wave", label: "Wave")
                    QuickActionWidget(icon: "heart.fill", label: "Flirt")
                    QuickActionWidget(icon: "message.fill", label: "Chat")
                }
            }
            .padding()
        }
    }
}

struct QuickActionWidget: View {
    let icon: String
    let label: String

    var body: some View {
        Link(destination: URL(string: "atlas://action/\(label.lowercased())")!) {
            VStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.title3)
                Text(label)
                    .font(.caption2)
            }
            .foregroundColor(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(.white.opacity(0.2))
            .cornerRadius(10)
        }
    }
}

// MARK: - Widget Configuration

@main
struct SAMWidget: Widget {
    let kind: String = "SAMWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: SAMWidgetProvider()) { entry in
            SAMWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("SAM")
        .description("Quick access to your AI companion")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}

struct SAMWidgetEntryView: View {
    @Environment(\.widgetFamily) var family
    let entry: SAMWidgetEntry

    var body: some View {
        switch family {
        case .systemSmall:
            SAMWidgetSmall(entry: entry)
        case .systemMedium:
            SAMWidgetMedium(entry: entry)
        case .systemLarge:
            SAMWidgetLarge(entry: entry)
        default:
            SAMWidgetSmall(entry: entry)
        }
    }
}

#Preview("Small", as: .systemSmall) {
    SAMWidget()
} timeline: {
    SAMWidgetEntry(date: Date(), mood: "playful", moodEmoji: "😏", lastMessage: "Hey you...", isConnected: true)
}

#Preview("Medium", as: .systemMedium) {
    SAMWidget()
} timeline: {
    SAMWidgetEntry(date: Date(), mood: "happy", moodEmoji: "😊", lastMessage: "Good morning! Ready for the day?", isConnected: true)
}

#Preview("Large", as: .systemLarge) {
    SAMWidget()
} timeline: {
    SAMWidgetEntry(date: Date(), mood: "flirty", moodEmoji: "😈", lastMessage: "I've been thinking about you...", isConnected: true)
}
