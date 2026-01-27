import SwiftUI
import Charts

// MARK: - Browse View

struct BrowseView: View {
    @EnvironmentObject var archiveService: ArchiveService
    @State private var selectedSource: String?
    @State private var selectedCategory: String?
    @State private var selectedArticle: Article?

    var body: some View {
        VStack {
            // Filters
            HStack {
                Picker("Source", selection: $selectedSource) {
                    Text("All Sources").tag(nil as String?)
                    ForEach(archiveService.sources) { source in
                        Text(source.name).tag(source.source as String?)
                    }
                }
                .pickerStyle(.menu)

                Picker("Category", selection: $selectedCategory) {
                    Text("All Categories").tag(nil as String?)
                    ForEach(Array(archiveService.categories.keys.sorted().prefix(20)), id: \.self) { cat in
                        Text(cat.capitalized).tag(cat as String?)
                    }
                }
                .pickerStyle(.menu)

                Spacer()

                if let stats = archiveService.stats {
                    Text("\(stats.totalArticles.formatted()) articles")
                        .foregroundColor(.secondary)
                }
            }
            .padding(.horizontal)

            // Article List
            List(archiveService.articles.isEmpty ? archiveService.searchResults : archiveService.articles, selection: $selectedArticle) { article in
                ArticleRow(article: article)
                    .tag(article)
            }
            .listStyle(.inset)
        }
        .navigationTitle("Browse")
        .sheet(item: $selectedArticle) { article in
            ArticleDetailView(article: article)
        }
        .onChange(of: selectedSource) { _, _ in
            Task {
                await archiveService.loadArticles(source: selectedSource, category: selectedCategory)
            }
        }
        .onChange(of: selectedCategory) { _, _ in
            Task {
                await archiveService.loadArticles(source: selectedSource, category: selectedCategory)
            }
        }
        .task {
            await archiveService.loadArticles()
        }
    }
}

// MARK: - Article Row

struct ArticleRow: View {
    let article: Article

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(article.title)
                .font(.headline)
                .lineLimit(2)

            HStack {
                Text(article.sourceName ?? article.source)
                    .font(.caption)
                    .foregroundColor(.blue)

                Text("•")
                    .foregroundColor(.secondary)

                Text(article.formattedDate)
                    .font(.caption)
                    .foregroundColor(.secondary)

                if let wordCount = article.wordCount {
                    Text("•")
                        .foregroundColor(.secondary)
                    Text("\(wordCount) words")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            if let category = article.category {
                Text(category.capitalized)
                    .font(.caption2)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(4)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Article Detail View

struct ArticleDetailView: View {
    @EnvironmentObject var archiveService: ArchiveService
    let article: Article
    @State private var isSpeaking = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Header
                VStack(alignment: .leading, spacing: 8) {
                    Text(article.title)
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    HStack {
                        if let author = article.author {
                            Text("By \(author)")
                                .font(.subheadline)
                        }
                        Text("•")
                        Text(article.sourceName ?? article.source)
                            .foregroundColor(.blue)
                        Text("•")
                        Text(article.formattedDate)
                    }
                    .foregroundColor(.secondary)

                    // Actions
                    HStack {
                        Button {
                            if isSpeaking {
                                archiveService.stopSpeaking()
                            } else {
                                archiveService.speak(article.content ?? "")
                            }
                            isSpeaking.toggle()
                        } label: {
                            Label(isSpeaking ? "Stop" : "Read Aloud", systemImage: isSpeaking ? "stop.fill" : "speaker.wave.2")
                        }

                        if let url = article.url, let articleURL = URL(string: url) {
                            Link("Open Original", destination: articleURL)
                        }
                    }
                    .padding(.top, 8)
                }

                Divider()

                // Content
                if let content = article.content {
                    Text(content)
                        .font(.body)
                        .lineSpacing(6)
                }

                // Metadata
                if let wordCount = article.wordCount {
                    HStack {
                        Label("\(wordCount) words", systemImage: "text.word.spacing")
                        if let imageCount = article.imageCount, imageCount > 0 {
                            Label("\(imageCount) images", systemImage: "photo")
                        }
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.top)
                }
            }
            .padding()
        }
        .frame(minWidth: 600, minHeight: 400)
    }
}

// MARK: - Article Card (for tvOS)

struct ArticleCard: View {
    let article: Article

    var body: some View {
        VStack(alignment: .leading) {
            Text(article.title)
                .font(.headline)
                .lineLimit(3)

            Spacer()

            HStack {
                Text(article.sourceName ?? article.source)
                    .font(.caption)
                Spacer()
                Text(article.formattedDate)
                    .font(.caption)
            }
            .foregroundColor(.secondary)
        }
        .padding()
        .background(Color.gray.opacity(0.2))
        .cornerRadius(12)
    }
}

// MARK: - Analytics View

struct AnalyticsView: View {
    @EnvironmentObject var archiveService: ArchiveService
    @State private var trendTerm = ""
    @State private var selectedTab = 0

    var body: some View {
        VStack {
            Picker("View", selection: $selectedTab) {
                Text("Overview").tag(0)
                Text("Trends").tag(1)
                Text("Categories").tag(2)
            }
            .pickerStyle(.segmented)
            .padding()

            switch selectedTab {
            case 0:
                OverviewTab()
            case 1:
                TrendsTab(trendTerm: $trendTerm)
            case 2:
                CategoriesTab()
            default:
                EmptyView()
            }
        }
        .navigationTitle("Analytics")
    }
}

// MARK: - Overview Tab

struct OverviewTab: View {
    @EnvironmentObject var archiveService: ArchiveService

    var body: some View {
        ScrollView {
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 20) {
                // Total Articles
                StatCard(
                    title: "Total Articles",
                    value: archiveService.stats?.totalArticles.formatted() ?? "0",
                    icon: "doc.text"
                )

                // Total Words
                StatCard(
                    title: "Total Words",
                    value: formatLargeNumber(archiveService.stats?.totalWords ?? 0),
                    icon: "text.word.spacing"
                )

                // Sources
                StatCard(
                    title: "Sources",
                    value: "\(archiveService.sources.count)",
                    icon: "newspaper"
                )

                // Categories
                StatCard(
                    title: "Categories",
                    value: "\(archiveService.categories.count)",
                    icon: "folder"
                )
            }
            .padding()

            // Year Chart
            if let stats = archiveService.stats, !stats.byYear.isEmpty {
                VStack(alignment: .leading) {
                    Text("Articles by Year")
                        .font(.headline)
                        .padding(.horizontal)

                    Chart {
                        ForEach(stats.byYear.sorted(by: { $0.key < $1.key }), id: \.key) { year, count in
                            BarMark(
                                x: .value("Year", year),
                                y: .value("Articles", count)
                            )
                            .foregroundStyle(.blue.gradient)
                        }
                    }
                    .frame(height: 200)
                    .padding()
                }
            }
        }
    }

    func formatLargeNumber(_ n: Int) -> String {
        if n >= 1_000_000 {
            return String(format: "%.1fM", Double(n) / 1_000_000)
        } else if n >= 1000 {
            return String(format: "%.1fK", Double(n) / 1000)
        }
        return n.formatted()
    }
}

// MARK: - Stat Card

struct StatCard: View {
    let title: String
    let value: String
    let icon: String

    var body: some View {
        VStack {
            Image(systemName: icon)
                .font(.largeTitle)
                .foregroundColor(.blue)

            Text(value)
                .font(.title)
                .fontWeight(.bold)

            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
    }
}

// MARK: - Trends Tab

struct TrendsTab: View {
    @EnvironmentObject var archiveService: ArchiveService
    @Binding var trendTerm: String

    var body: some View {
        VStack {
            HStack {
                TextField("Enter term to analyze", text: $trendTerm)
                    .textFieldStyle(.roundedBorder)

                Button("Analyze") {
                    Task {
                        await archiveService.loadTrend(term: trendTerm)
                    }
                }
                .disabled(trendTerm.isEmpty)
            }
            .padding()

            if let trend = archiveService.currentTrend, !trend.data.isEmpty {
                Chart {
                    ForEach(trend.data) { point in
                        LineMark(
                            x: .value("Period", point.period),
                            y: .value("Mentions", point.mentions)
                        )
                        .foregroundStyle(.blue)

                        PointMark(
                            x: .value("Period", point.period),
                            y: .value("Mentions", point.mentions)
                        )
                        .foregroundStyle(.blue)
                    }
                }
                .frame(height: 300)
                .padding()

                Text("'\(trend.term)' mentioned \(trend.data.map { $0.mentions }.reduce(0, +)) times")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                ContentUnavailableView(
                    "No Trend Data",
                    systemImage: "chart.line.uptrend.xyaxis",
                    description: Text("Enter a term above to see how it trends over time")
                )
            }

            Spacer()
        }
    }
}

// MARK: - Categories Tab

struct CategoriesTab: View {
    @EnvironmentObject var archiveService: ArchiveService

    var body: some View {
        List {
            ForEach(archiveService.categories.sorted(by: { $0.value > $1.value }), id: \.key) { category, count in
                HStack {
                    Text(category.capitalized)
                    Spacer()
                    Text("\(count)")
                        .foregroundColor(.secondary)
                }
            }
        }
    }
}

// MARK: - SAM Chat View

struct SAMChatView: View {
    @EnvironmentObject var archiveService: ArchiveService
    @State private var messageText = ""

    var body: some View {
        VStack {
            // Chat Messages
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(archiveService.chatMessages) { message in
                        ChatBubble(message: message)
                    }
                }
                .padding()
            }

            Divider()

            // Input
            HStack {
                TextField("Ask SAM about fashion...", text: $messageText)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        sendMessage()
                    }

                Button {
                    sendMessage()
                } label: {
                    Image(systemName: "paperplane.fill")
                }
                .disabled(messageText.isEmpty)
            }
            .padding()
        }
        .navigationTitle("SAM")
    }

    func sendMessage() {
        guard !messageText.isEmpty else { return }
        let message = messageText
        messageText = ""
        Task {
            await archiveService.sendToSAM(message)
        }
    }
}

// MARK: - Chat Bubble

struct ChatBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack {
            if message.role == .user {
                Spacer()
            }

            VStack(alignment: message.role == .user ? .trailing : .leading) {
                Text(message.content)
                    .padding(12)
                    .background(message.role == .user ? Color.blue : Color.gray.opacity(0.2))
                    .foregroundColor(message.role == .user ? .white : .primary)
                    .cornerRadius(16)

                Text(message.timestamp, style: .time)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            if message.role != .user {
                Spacer()
            }
        }
    }
}

// MARK: - Settings View

struct SettingsView: View {
    @EnvironmentObject var archiveService: ArchiveService
    @AppStorage("apiBaseURL") var apiBaseURL = "http://localhost:8420"

    var body: some View {
        Form {
            Section("API Configuration") {
                TextField("API Base URL", text: $apiBaseURL)
                    .textFieldStyle(.roundedBorder)

                Button("Test Connection") {
                    Task {
                        await archiveService.loadStats()
                    }
                }
            }

            Section("Archive Status") {
                if let stats = archiveService.stats {
                    LabeledContent("Total Articles", value: stats.totalArticles.formatted())
                    LabeledContent("Total Words", value: stats.totalWords.formatted())
                    LabeledContent("Sources", value: "\(stats.bySource.count)")
                } else {
                    Text("Not connected")
                        .foregroundColor(.secondary)
                }
            }

            Section("About") {
                LabeledContent("Version", value: "1.0.0")
                LabeledContent("Platform", value: platformName)
            }
        }
        .formStyle(.grouped)
        .navigationTitle("Settings")
    }

    var platformName: String {
        #if os(macOS)
        return "macOS"
        #elseif os(iOS)
        return "iOS"
        #elseif os(tvOS)
        return "tvOS"
        #else
        return "Unknown"
        #endif
    }
}
