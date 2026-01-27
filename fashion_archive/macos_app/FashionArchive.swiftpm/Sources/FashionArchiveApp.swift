import SwiftUI

@main
struct FashionArchiveApp: App {
    @StateObject private var archiveService = ArchiveService()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(archiveService)
        }
        #if os(macOS)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("Search Articles") {
                    NSApp.sendAction(#selector(NSResponder.becomeFirstResponder), to: nil, from: nil)
                }
                .keyboardShortcut("f", modifiers: [.command])
            }
        }

        Settings {
            SettingsView()
                .environmentObject(archiveService)
        }
        #endif
    }
}

// MARK: - Content View (Platform Adaptive)

struct ContentView: View {
    @EnvironmentObject var archiveService: ArchiveService

    var body: some View {
        #if os(tvOS)
        TVContentView()
        #elseif os(macOS)
        MacContentView()
        #else
        MobileContentView()
        #endif
    }
}

// MARK: - macOS Layout

#if os(macOS)
struct MacContentView: View {
    @EnvironmentObject var archiveService: ArchiveService
    @State private var selectedTab: Tab = .browse
    @State private var searchText = ""

    enum Tab: Hashable {
        case browse, analytics, sam, settings
    }

    var body: some View {
        NavigationSplitView {
            List(selection: $selectedTab) {
                Section("Library") {
                    Label("Browse", systemImage: "books.vertical")
                        .tag(Tab.browse)
                    Label("Analytics", systemImage: "chart.bar.xaxis")
                        .tag(Tab.analytics)
                    Label("SAM", systemImage: "brain")
                        .tag(Tab.sam)
                }

                Section("Sources") {
                    ForEach(archiveService.sources, id: \.source) { source in
                        HStack {
                            Text(source.name)
                            Spacer()
                            Text("\(source.count)")
                                .foregroundColor(.secondary)
                        }
                    }
                }
            }
            .listStyle(.sidebar)
            .frame(minWidth: 200)
        } detail: {
            switch selectedTab {
            case .browse:
                BrowseView()
            case .analytics:
                AnalyticsView()
            case .sam:
                SAMChatView()
            case .settings:
                SettingsView()
            }
        }
        .searchable(text: $searchText, prompt: "Search articles...")
        .onSubmit(of: .search) {
            archiveService.search(query: searchText)
        }
        .task {
            await archiveService.loadStats()
        }
    }
}
#endif

// MARK: - iOS/iPadOS Layout

#if os(iOS)
struct MobileContentView: View {
    @EnvironmentObject var archiveService: ArchiveService
    @State private var searchText = ""

    var body: some View {
        TabView {
            NavigationStack {
                BrowseView()
                    .searchable(text: $searchText)
            }
            .tabItem {
                Label("Browse", systemImage: "books.vertical")
            }

            NavigationStack {
                AnalyticsView()
            }
            .tabItem {
                Label("Analytics", systemImage: "chart.bar.xaxis")
            }

            NavigationStack {
                SAMChatView()
            }
            .tabItem {
                Label("SAM", systemImage: "brain")
            }

            NavigationStack {
                SettingsView()
            }
            .tabItem {
                Label("Settings", systemImage: "gear")
            }
        }
        .task {
            await archiveService.loadStats()
        }
    }
}
#endif

// MARK: - tvOS Layout

#if os(tvOS)
struct TVContentView: View {
    @EnvironmentObject var archiveService: ArchiveService
    @State private var selectedCategory: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 40) {
                    // Featured Section
                    Text("Fashion Archive")
                        .font(.largeTitle)
                        .padding(.horizontal)

                    // Categories
                    ForEach(Array(archiveService.categories.keys.sorted().prefix(5)), id: \.self) { category in
                        VStack(alignment: .leading) {
                            Text(category.capitalized)
                                .font(.headline)
                                .padding(.horizontal)

                            ScrollView(.horizontal) {
                                LazyHStack(spacing: 20) {
                                    ForEach(archiveService.articles.filter { $0.category == category }.prefix(10)) { article in
                                        ArticleCard(article: article)
                                            .frame(width: 400, height: 250)
                                    }
                                }
                                .padding(.horizontal)
                            }
                        }
                    }
                }
            }
        }
        .task {
            await archiveService.loadStats()
            await archiveService.loadArticles()
        }
    }
}
#endif
