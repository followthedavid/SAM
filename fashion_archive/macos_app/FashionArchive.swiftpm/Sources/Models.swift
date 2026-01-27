import Foundation

// MARK: - Article Model

struct Article: Identifiable, Codable, Hashable {
    let id: String
    let source: String
    let sourceName: String?
    let url: String?
    let title: String
    let author: String?
    let category: String?
    let subcategory: String?
    let publishDate: String?
    let content: String?
    let wordCount: Int?
    let imageCount: Int?
    let tags: String?

    enum CodingKeys: String, CodingKey {
        case id, source, url, title, author, category, subcategory, content, tags
        case sourceName = "source_name"
        case publishDate = "publish_date"
        case wordCount = "word_count"
        case imageCount = "image_count"
    }

    var formattedDate: String {
        guard let date = publishDate else { return "Unknown date" }
        return String(date.prefix(10))
    }

    var excerpt: String {
        guard let content = content else { return "" }
        return String(content.prefix(200)) + (content.count > 200 ? "..." : "")
    }
}

// MARK: - Stats Model

struct ArchiveStats: Codable {
    let totalArticles: Int
    let totalWords: Int
    let totalImages: Int
    let bySource: [SourceStats]
    let byYear: [String: Int]
    let topCategories: [String: Int]

    enum CodingKeys: String, CodingKey {
        case totalArticles = "total_articles"
        case totalWords = "total_words"
        case totalImages = "total_images"
        case bySource = "by_source"
        case byYear = "by_year"
        case topCategories = "top_categories"
    }
}

struct SourceStats: Codable, Identifiable {
    let source: String
    let name: String
    let count: Int
    let words: Int

    var id: String { source }
}

// MARK: - Trend Model

struct TrendData: Codable {
    let term: String
    let by: String
    let data: [TrendPoint]
}

struct TrendPoint: Codable, Identifiable {
    let period: String
    let mentions: Int

    var id: String { period }

    var year: Int? {
        Int(period)
    }
}

// MARK: - Search Response

struct SearchResponse: Codable {
    let query: String?
    let count: Int
    let articles: [Article]
}

// MARK: - SAM Context

struct SAMContext: Codable {
    let topic: String
    let articles: [SAMArticleContext]
}

struct SAMArticleContext: Codable, Identifiable {
    let title: String
    let source: String
    let date: String?
    let excerpt: String

    var id: String { title }
}

// MARK: - Chat Message

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: Role
    let content: String
    let timestamp: Date

    enum Role {
        case user, assistant, system
    }
}

// MARK: - API Response Wrapper

struct APIResponse<T: Codable>: Codable {
    let data: T?
    let error: String?
}
