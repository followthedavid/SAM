import Foundation
import SwiftUI
#if canImport(AVFoundation)
import AVFoundation
#endif

// MARK: - Archive Service

@MainActor
class ArchiveService: ObservableObject {
    // MARK: - Published Properties

    @Published var stats: ArchiveStats?
    @Published var articles: [Article] = []
    @Published var searchResults: [Article] = []
    @Published var sources: [SourceStats] = []
    @Published var categories: [String: Int] = [:]
    @Published var currentTrend: TrendData?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var chatMessages: [ChatMessage] = []

    // MARK: - Configuration

    @AppStorage("apiBaseURL") var apiBaseURL = "http://localhost:8420"

    // MARK: - Speech

    #if os(macOS)
    private let speechSynthesizer = NSSpeechSynthesizer()
    #elseif os(iOS) || os(tvOS)
    private let speechSynthesizer = AVSpeechSynthesizer()
    #endif

    // MARK: - API Methods

    private func apiURL(_ path: String) -> URL? {
        URL(string: "\(apiBaseURL)\(path)")
    }

    private func fetch<T: Codable>(_ path: String) async throws -> T {
        guard let url = apiURL(path) else {
            throw URLError(.badURL)
        }

        let (data, _) = try await URLSession.shared.data(from: url)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func post<T: Codable, R: Codable>(_ path: String, body: T) async throws -> R {
        guard let url = apiURL(path) else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)

        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(R.self, from: data)
    }

    // MARK: - Load Data

    func loadStats() async {
        isLoading = true
        defer { isLoading = false }

        do {
            stats = try await fetch("/stats")
            sources = stats?.bySource ?? []
            categories = stats?.topCategories ?? [:]
        } catch {
            errorMessage = "Failed to load stats: \(error.localizedDescription)"
        }
    }

    func loadArticles(source: String? = nil, category: String? = nil, limit: Int = 50) async {
        isLoading = true
        defer { isLoading = false }

        var path = "/articles?limit=\(limit)"
        if let source = source {
            path += "&source=\(source)"
        }
        if let category = category {
            path += "&category=\(category.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? category)"
        }

        do {
            let response: SearchResponse = try await fetch(path)
            articles = response.articles
        } catch {
            errorMessage = "Failed to load articles: \(error.localizedDescription)"
        }
    }

    func search(query: String, source: String? = nil, limit: Int = 50) {
        Task {
            isLoading = true
            defer { isLoading = false }

            var path = "/search?q=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query)&limit=\(limit)"
            if let source = source {
                path += "&source=\(source)"
            }

            do {
                let response: SearchResponse = try await fetch(path)
                searchResults = response.articles
            } catch {
                errorMessage = "Search failed: \(error.localizedDescription)"
            }
        }
    }

    func getArticle(id: String) async -> Article? {
        do {
            return try await fetch("/articles/\(id)")
        } catch {
            errorMessage = "Failed to load article: \(error.localizedDescription)"
            return nil
        }
    }

    // MARK: - Analytics

    func loadTrend(term: String, by: String = "year") async {
        do {
            currentTrend = try await fetch("/trends/\(term.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? term)?by=\(by)")
        } catch {
            errorMessage = "Failed to load trend: \(error.localizedDescription)"
        }
    }

    // MARK: - Speech

    func speak(_ text: String) {
        #if os(macOS)
        speechSynthesizer.stopSpeaking()
        speechSynthesizer.startSpeaking(text)
        #elseif os(iOS) || os(tvOS)
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = 0.5
        speechSynthesizer.speak(utterance)
        #endif
    }

    func stopSpeaking() {
        #if os(macOS)
        speechSynthesizer.stopSpeaking()
        #elseif os(iOS) || os(tvOS)
        speechSynthesizer.stopSpeaking(at: .immediate)
        #endif
    }

    // MARK: - SAM Chat

    func sendToSAM(_ message: String) async {
        // Add user message
        chatMessages.append(ChatMessage(role: .user, content: message, timestamp: Date()))

        do {
            // Get context from archive
            let context: SAMContext = try await fetch("/sam/context/\(message.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? message)?limit=3")

            // Build response (in real implementation, this would call SAM's API)
            var response = "Based on the Fashion Archive, I found \(context.articles.count) relevant articles:\n\n"

            for article in context.articles {
                response += "**\(article.title)** (\(article.source), \(article.date ?? "Unknown date"))\n"
                response += "\(article.excerpt)\n\n"
            }

            chatMessages.append(ChatMessage(role: .assistant, content: response, timestamp: Date()))
        } catch {
            chatMessages.append(ChatMessage(
                role: .system,
                content: "Error: \(error.localizedDescription)",
                timestamp: Date()
            ))
        }
    }
}
