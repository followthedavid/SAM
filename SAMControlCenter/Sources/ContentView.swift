import SwiftUI
import UniformTypeIdentifiers
import ScreenCaptureKit

// MARK: - Main Tab View

struct ContentView: View {
    @EnvironmentObject var samState: SAMState
    @State private var selectedTab = 0

    var body: some View {
        ZStack {
            // Animated gradient background
            AnimatedGradientBackground()

            VStack(spacing: 0) {
                // Project Status + Tab Bar
                HeaderView(selectedTab: $selectedTab)
                    .environmentObject(samState)

                // Tab Content
                TabView(selection: $selectedTab) {
                    ChatView()
                        .environmentObject(samState)
                        .tag(0)

                    RoleplayView()
                        .environmentObject(samState)
                        .tag(1)

                    ApprovalQueueView()
                        .environmentObject(samState)
                        .tag(2)

                    ControlView()
                        .environmentObject(samState)
                        .tag(3)

                    CodeView()
                        .environmentObject(samState)
                        .tag(4)

                    VoiceView()
                        .environmentObject(samState)
                        .tag(5)
                }
                .tabViewStyle(.automatic)
            }
        }
        .frame(minWidth: 700, minHeight: 550)
    }
}

// MARK: - Header View (Project Status + Tabs)

struct HeaderView: View {
    @Binding var selectedTab: Int
    @EnvironmentObject var samState: SAMState

    var body: some View {
        VStack(spacing: 0) {
            // Project Status Indicator
            ProjectStatusIndicator()
                .environmentObject(samState)

            // Tab Bar
            TabBarView(selectedTab: $selectedTab)
        }
    }
}

// MARK: - Project Status Indicator

struct ProjectStatusIndicator: View {
    @EnvironmentObject var samState: SAMState
    @State private var currentProject: ProjectInfo? = nil
    @State private var isLoading = true

    private var timer = Timer.publish(every: 10, on: .main, in: .common).autoconnect()

    var body: some View {
        HStack(spacing: 8) {
            if isLoading {
                ProgressView()
                    .scaleEffect(0.6)
                    .frame(width: 14, height: 14)
            } else if let project = currentProject {
                // Project icon
                Image(systemName: project.icon)
                    .font(.system(size: 11))
                    .foregroundStyle(statusColor(project.status))

                // Project name
                Text(project.name)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.white.opacity(0.9))

                // Status badge
                Text(project.status.capitalized)
                    .font(.system(size: 9, weight: .medium))
                    .foregroundStyle(statusColor(project.status))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(
                        Capsule()
                            .fill(statusColor(project.status).opacity(0.2))
                    )

                // Type indicator
                if let type = project.type {
                    Text(type)
                        .font(.system(size: 9))
                        .foregroundStyle(.secondary)
                }
            } else {
                Image(systemName: "folder.badge.questionmark")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                Text("No project")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }

            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 6)
        .background(.black.opacity(0.2))
        .onAppear {
            fetchCurrentProject()
        }
        .onReceive(timer) { _ in
            fetchCurrentProject()
        }
    }

    func statusColor(_ status: String) -> Color {
        switch status.lowercased() {
        case "active", "running":
            return .green
        case "building", "in_progress":
            return .cyan
        case "paused":
            return .orange
        case "archived", "stopped":
            return .gray
        case "error":
            return .red
        default:
            return .blue
        }
    }

    func fetchCurrentProject() {
        Task {
            await MainActor.run { isLoading = true }

            guard let url = URL(string: "http://localhost:8765/api/project/current") else {
                await MainActor.run {
                    currentProject = nil
                    isLoading = false
                }
                return
            }

            var request = URLRequest(url: url)
            request.timeoutInterval = 5

            do {
                let (data, _) = try await URLSession.shared.data(for: request)
                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let projectDict = json["project"] as? [String: Any] {
                    await MainActor.run {
                        currentProject = ProjectInfo(
                            name: projectDict["name"] as? String ?? "Unknown",
                            type: projectDict["type"] as? String,
                            status: projectDict["status"] as? String ?? "unknown",
                            icon: projectDict["icon"] as? String ?? "folder.fill",
                            path: projectDict["path"] as? String
                        )
                        isLoading = false
                    }
                } else {
                    await MainActor.run {
                        currentProject = nil
                        isLoading = false
                    }
                }
            } catch {
                await MainActor.run {
                    currentProject = nil
                    isLoading = false
                }
            }
        }
    }
}

struct ProjectInfo {
    let name: String
    let type: String?
    let status: String
    let icon: String
    let path: String?
}

// MARK: - Tab Bar

struct TabBarView: View {
    @Binding var selectedTab: Int
    @EnvironmentObject var samState: SAMState

    let tabs = [
        ("Chat", "bubble.left.fill"),
        ("Roleplay", "theatermasks.fill"),
        ("Pending", "checkmark.shield.fill"),
        ("Control", "slider.horizontal.3"),
        ("Code", "terminal.fill"),
        ("Voice", "waveform")
    ]

    var body: some View {
        HStack(spacing: 0) {
            ForEach(Array(tabs.enumerated()), id: \.offset) { index, tab in
                if tab.0 == "Pending" {
                    TabButtonWithBadge(
                        title: tab.0,
                        icon: tab.1,
                        isSelected: selectedTab == index,
                        badgeCount: samState.pendingApprovals.count
                    ) {
                        withAnimation(.spring(response: 0.3)) {
                            selectedTab = index
                        }
                    }
                } else {
                    TabButton(
                        title: tab.0,
                        icon: tab.1,
                        isSelected: selectedTab == index
                    ) {
                        withAnimation(.spring(response: 0.3)) {
                            selectedTab = index
                        }
                    }
                }
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(.regularMaterial)
    }
}

struct TabButton: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                Text(title)
                    .font(.system(size: 13, weight: .medium))
            }
            .foregroundStyle(isSelected ? .white : .secondary)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.accentColor.opacity(0.8) : Color.clear)
            )
        }
        .buttonStyle(.plain)
    }
}

struct TabButtonWithBadge: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let badgeCount: Int
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                Text(title)
                    .font(.system(size: 13, weight: .medium))

                if badgeCount > 0 {
                    Text("\(badgeCount)")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Capsule().fill(Color.orange))
                }
            }
            .foregroundStyle(isSelected ? .white : .secondary)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.accentColor.opacity(0.8) : Color.clear)
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Chat View

struct ChatView: View {
    @EnvironmentObject var samState: SAMState
    @State private var messageText = ""
    @State private var messages: [ChatMessage] = [
        ChatMessage(role: .assistant, content: "Hey there. What's on your mind?")
    ]
    @State private var isLoading = false
    @State private var selectedImageData: Data? = nil
    @State private var selectedImageThumbnail: NSImage? = nil
    @State private var isDraggingOver = false

    var body: some View {
        VStack(spacing: 0) {
            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(Array(messages.enumerated()), id: \.element.id) { index, message in
                            MessageBubble(message: message) { rating, correction in
                                submitFeedback(for: index, rating: rating, correction: correction)
                            }
                            .environmentObject(samState)
                        }

                        if isLoading {
                            HStack {
                                ProgressView()
                                    .scaleEffect(0.8)
                                Text("SAM is thinking...")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                            }
                            .padding(.horizontal)
                        }
                    }
                    .padding()
                }
                .onChange(of: messages.count) { _, _ in
                    if let last = messages.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
            .onDrop(of: [.image, .fileURL], isTargeted: $isDraggingOver) { providers in
                handleImageDrop(providers: providers)
                return true
            }
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isDraggingOver ? Color.cyan : Color.clear, lineWidth: 2)
                    .padding(4)
            )

            // Selected image preview
            if let thumbnail = selectedImageThumbnail {
                HStack(spacing: 12) {
                    // Thumbnail preview
                    ZStack(alignment: .topTrailing) {
                        Image(nsImage: thumbnail)
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 60, height: 60)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.cyan.opacity(0.5), lineWidth: 1)
                            )

                        // Remove button
                        Button(action: clearSelectedImage) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 16))
                                .foregroundStyle(.white)
                                .background(Circle().fill(Color.black.opacity(0.6)))
                        }
                        .buttonStyle(.plain)
                        .offset(x: 6, y: -6)
                    }

                    Text("Image attached")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Spacer()
                }
                .padding(.horizontal)
                .padding(.top, 8)
                .background(.regularMaterial)
            }

            // Input
            HStack(spacing: 12) {
                // Image picker button
                Button(action: pickImage) {
                    Image(systemName: "photo.badge.plus")
                        .font(.system(size: 20))
                        .foregroundStyle(.cyan.opacity(0.8))
                }
                .buttonStyle(.plain)
                .help("Attach an image (or paste with Cmd+V)")

                // Screenshot capture button
                Button(action: captureScreenshot) {
                    Image(systemName: "camera.viewfinder")
                        .font(.system(size: 20))
                        .foregroundStyle(.orange.opacity(0.8))
                }
                .buttonStyle(.plain)
                .help("Capture screenshot (Cmd+Shift+S)")
                .keyboardShortcut("s", modifiers: [.command, .shift])

                TextField("Message SAM...", text: $messageText)
                    .textFieldStyle(.plain)
                    .padding(12)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .onSubmit {
                        sendMessage()
                    }

                Button(action: sendMessage) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 28))
                        .foregroundStyle(.cyan)
                }
                .buttonStyle(.plain)
                .disabled((messageText.isEmpty && selectedImageData == nil) || isLoading)
            }
            .padding()
            .background(.regularMaterial)
        }
        // Handle Cmd+V paste for images
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
            // Set up paste handler when window becomes active
            NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
                if event.modifierFlags.contains(.command) && event.charactersIgnoringModifiers == "v" {
                    if handlePasteImage() {
                        return nil  // Consume the event if we handled an image paste
                    }
                }
                return event
            }
        }
    }

    // MARK: - Paste Image Handler

    func handlePasteImage() -> Bool {
        let pasteboard = NSPasteboard.general

        // Check for image types in pasteboard
        let imageTypes: [NSPasteboard.PasteboardType] = [.png, .tiff]

        for type in imageTypes {
            if let data = pasteboard.data(forType: type),
               let image = NSImage(data: data) {
                selectedImageData = data
                selectedImageThumbnail = image
                return true
            }
        }

        // Check for file URLs that are images
        if let urls = pasteboard.readObjects(forClasses: [NSURL.self], options: nil) as? [URL] {
            for url in urls {
                if let uti = try? url.resourceValues(forKeys: [.typeIdentifierKey]).typeIdentifier,
                   UTType(uti)?.conforms(to: .image) == true {
                    loadImage(from: url)
                    return true
                }
            }
        }

        return false
    }

    func pickImage() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.allowedContentTypes = [.image, .png, .jpeg, .gif, .heic]

        if panel.runModal() == .OK, let url = panel.url {
            loadImage(from: url)
        }
    }

    func loadImage(from url: URL) {
        guard let data = try? Data(contentsOf: url),
              let image = NSImage(data: data) else {
            return
        }

        selectedImageData = data
        selectedImageThumbnail = image
    }

    func handleImageDrop(providers: [NSItemProvider]) {
        for provider in providers {
            // Handle file URLs
            if provider.hasItemConformingToTypeIdentifier("public.file-url") {
                provider.loadItem(forTypeIdentifier: "public.file-url", options: nil) { item, error in
                    guard let data = item as? Data,
                          let url = URL(dataRepresentation: data, relativeTo: nil) else {
                        return
                    }

                    DispatchQueue.main.async {
                        loadImage(from: url)
                    }
                }
                return
            }

            // Handle image data directly
            if provider.hasItemConformingToTypeIdentifier("public.image") {
                provider.loadDataRepresentation(forTypeIdentifier: "public.image") { data, error in
                    guard let data = data,
                          let image = NSImage(data: data) else {
                        return
                    }

                    DispatchQueue.main.async {
                        selectedImageData = data
                        selectedImageThumbnail = image
                    }
                }
                return
            }
        }
    }

    func clearSelectedImage() {
        selectedImageData = nil
        selectedImageThumbnail = nil
    }

    // MARK: - Screenshot Capture

    func captureScreenshot() {
        Task {
            await captureFullScreen()
        }
    }

    @MainActor
    func captureFullScreen() async {
        // Use CGWindowListCreateImage for simple full-screen capture
        // This captures the entire screen without requiring ScreenCaptureKit permissions initially
        let displayID = CGMainDisplayID()

        // Capture the entire main display
        guard let screenshot = CGDisplayCreateImage(displayID) else {
            print("Failed to capture screenshot")
            return
        }

        // Convert CGImage to NSImage and then to Data
        let nsImage = NSImage(cgImage: screenshot, size: NSSize(width: screenshot.width, height: screenshot.height))

        // Convert to PNG data
        guard let tiffData = nsImage.tiffRepresentation,
              let bitmapRep = NSBitmapImageRep(data: tiffData),
              let pngData = bitmapRep.representation(using: .png, properties: [:]) else {
            print("Failed to convert screenshot to PNG")
            return
        }

        // Set as selected image
        selectedImageData = pngData
        selectedImageThumbnail = nsImage
    }

    // Alternative: Use ScreenCaptureKit for more control (requires macOS 12.3+)
    @MainActor
    func captureWithScreenCaptureKit() async {
        do {
            // Get available content
            let content = try await SCShareableContent.current

            // Find main display
            guard let display = content.displays.first else {
                print("No displays found")
                return
            }

            // Create filter for the display only (no windows)
            let filter = SCContentFilter(display: display, excludingWindows: [])

            // Configure the stream
            let config = SCStreamConfiguration()
            config.width = display.width
            config.height = display.height
            config.pixelFormat = kCVPixelFormatType_32BGRA
            config.showsCursor = false

            // Capture a single frame
            let screenshot = try await SCScreenshotManager.captureImage(
                contentFilter: filter,
                configuration: config
            )

            // Convert to NSImage
            let nsImage = NSImage(cgImage: screenshot, size: NSSize(width: screenshot.width, height: screenshot.height))

            // Convert to PNG data
            guard let tiffData = nsImage.tiffRepresentation,
                  let bitmapRep = NSBitmapImageRep(data: tiffData),
                  let pngData = bitmapRep.representation(using: .png, properties: [:]) else {
                print("Failed to convert screenshot to PNG")
                return
            }

            // Set as selected image
            selectedImageData = pngData
            selectedImageThumbnail = nsImage

        } catch {
            print("ScreenCaptureKit error: \(error)")
            // Fall back to CGDisplay capture
            await captureFullScreen()
        }
    }

    func sendMessage() {
        guard !messageText.isEmpty || selectedImageData != nil else { return }

        // Create user message with optional image
        var userMessage = ChatMessage(
            role: .user,
            content: messageText,
            imageData: selectedImageData,
            isImageProcessing: selectedImageData != nil
        )

        messages.append(userMessage)
        let query = messageText
        let imageData = selectedImageData

        // Clear input
        messageText = ""
        clearSelectedImage()
        isLoading = true

        // Call SAM API
        Task {
            if let imageData = imageData {
                // Send image for analysis
                let (response, analysis) = await samState.analyzeImage(imageData: imageData, prompt: query)

                await MainActor.run {
                    // Update the user message with analysis result (remove processing indicator)
                    if let index = messages.firstIndex(where: { $0.id == userMessage.id }) {
                        messages[index].isImageProcessing = false
                        messages[index].imageAnalysis = analysis
                    }

                    // Add SAM's response if there's additional commentary
                    if !response.isEmpty && response != analysis {
                        messages.append(ChatMessage(role: .assistant, content: response))
                        // Auto-speak response if voice is enabled (Phase 6.1)
                        if samState.voiceEnabled {
                            Task { await samState.speak(text: response) }
                        }
                    }
                    isLoading = false
                }
            } else {
                // Regular text chat
                let response = await samState.chat(query)
                await MainActor.run {
                    messages.append(ChatMessage(role: .assistant, content: response))
                    // Auto-speak response if voice is enabled (Phase 6.1)
                    if samState.voiceEnabled {
                        Task { await samState.speak(text: response) }
                    }
                    isLoading = false
                }
            }
        }
    }

    func submitFeedback(for index: Int, rating: ChatMessage.FeedbackRating, correction: String?) {
        guard index < messages.count else { return }

        // Update local state
        messages[index].feedbackRating = rating

        // Submit to API
        let message = messages[index]
        Task {
            await samState.submitFeedback(
                responseId: message.id.uuidString,
                responseContent: message.content,
                rating: rating == .positive ? "positive" : "negative",
                correction: correction
            )
        }
    }
}

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: MessageRole
    let content: String
    let timestamp = Date()
    var feedbackRating: FeedbackRating? = nil

    // Image support
    var imageData: Data? = nil
    var imageAnalysis: String? = nil
    var isImageProcessing: Bool = false

    enum MessageRole {
        case user, assistant
    }

    enum FeedbackRating {
        case positive, negative
    }

    var hasImage: Bool {
        imageData != nil
    }

    // Convenience initializers
    init(role: MessageRole, content: String) {
        self.role = role
        self.content = content
        self.imageData = nil
        self.imageAnalysis = nil
        self.isImageProcessing = false
    }

    init(role: MessageRole, content: String, imageData: Data?, isImageProcessing: Bool = false) {
        self.role = role
        self.content = content
        self.imageData = imageData
        self.imageAnalysis = nil
        self.isImageProcessing = isImageProcessing
    }
}

struct MessageBubble: View {
    let message: ChatMessage
    var onFeedback: ((ChatMessage.FeedbackRating, String?) -> Void)? = nil
    @EnvironmentObject var samState: SAMState

    var body: some View {
        HStack {
            if message.role == .user { Spacer() }

            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 4) {
                // Image message bubble
                if message.hasImage {
                    ImageMessageContent(message: message)
                } else {
                    // Text-only message
                    Text(message.content)
                        .padding(12)
                        .background(
                            RoundedRectangle(cornerRadius: 16)
                                .fill(message.role == .user ? Color.cyan.opacity(0.3) : Color.white.opacity(0.1))
                        )
                        .foregroundStyle(.white)
                }

                HStack(spacing: 8) {
                    Text(message.timestamp, style: .time)
                        .font(.caption2)
                        .foregroundStyle(.secondary)

                    if message.role == .assistant {
                        // Speaker button for voice output (Phase 6.1)
                        MessageSpeakerButton(text: message.content)
                            .environmentObject(samState)

                        FeedbackButtons(
                            currentRating: message.feedbackRating,
                            onFeedback: { rating, correction in
                                onFeedback?(rating, correction)
                            }
                        )
                    }
                }
            }
            .frame(maxWidth: 400, alignment: message.role == .user ? .trailing : .leading)

            if message.role == .assistant { Spacer() }
        }
    }
}

// MARK: - Image Message Content

struct ImageMessageContent: View {
    let message: ChatMessage
    @State private var showFullSizeImage = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Image thumbnail
            if let imageData = message.imageData,
               let nsImage = NSImage(data: imageData) {
                Button(action: { showFullSizeImage = true }) {
                    Image(nsImage: nsImage)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(maxWidth: 300, maxHeight: 300)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.white.opacity(0.2), lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
                .sheet(isPresented: $showFullSizeImage) {
                    FullSizeImageView(imageData: imageData)
                }
            }

            // User's text (if any)
            if !message.content.isEmpty {
                Text(message.content)
                    .font(.body)
                    .foregroundStyle(.white)
            }

            // Processing indicator or SAM's analysis
            if message.isImageProcessing {
                VisionProgressIndicator()
            } else if let analysis = message.imageAnalysis {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 4) {
                        Image(systemName: "brain.fill")
                            .font(.caption2)
                            .foregroundStyle(.cyan)
                        Text("SAM's Analysis")
                            .font(.caption2)
                            .fontWeight(.medium)
                            .foregroundStyle(.cyan)
                    }

                    Text(analysis)
                        .font(.callout)
                        .foregroundStyle(.white.opacity(0.9))
                }
                .padding(10)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(Color.cyan.opacity(0.15))
                )
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(message.role == .user ? Color.cyan.opacity(0.3) : Color.white.opacity(0.1))
        )
    }
}

// MARK: - Vision Progress Indicator (Phase 3.1.8)

struct VisionProgressIndicator: View {
    @State private var elapsedSeconds: Int = 0
    @State private var currentPhase: String = "Preparing"
    @State private var phaseIndex: Int = 0

    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    private let phases = [
        (0, "Preparing image..."),
        (2, "Loading vision model..."),
        (10, "Analyzing image..."),
        (30, "Processing details..."),
        (60, "Almost done...")
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                // Animated brain icon
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 14))
                    .foregroundStyle(.cyan)
                    .symbolEffect(.pulse)

                VStack(alignment: .leading, spacing: 2) {
                    Text(currentPhase)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.9))
                        .italic()

                    Text(formatElapsed())
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .monospacedDigit()
                }

                Spacer()

                ProgressView()
                    .scaleEffect(0.6)
            }

            // Progress bar (estimated)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(.white.opacity(0.1))

                    RoundedRectangle(cornerRadius: 2)
                        .fill(
                            LinearGradient(
                                colors: [.cyan.opacity(0.8), .blue.opacity(0.8)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geo.size.width * estimatedProgress())
                        .animation(.easeInOut(duration: 0.5), value: elapsedSeconds)
                }
            }
            .frame(height: 3)

            // Helpful hint for long waits
            if elapsedSeconds > 15 {
                Text("Vision models need ~30-60s for detailed analysis")
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.7))
                    .transition(.opacity)
            }
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.cyan.opacity(0.1))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.cyan.opacity(0.2), lineWidth: 1)
                )
        )
        .onReceive(timer) { _ in
            elapsedSeconds += 1
            updatePhase()
        }
        .animation(.easeInOut(duration: 0.3), value: currentPhase)
    }

    private func formatElapsed() -> String {
        if elapsedSeconds < 60 {
            return "\(elapsedSeconds)s"
        } else {
            let mins = elapsedSeconds / 60
            let secs = elapsedSeconds % 60
            return "\(mins)m \(secs)s"
        }
    }

    private func estimatedProgress() -> Double {
        // Estimated progress based on typical 60s processing time
        let progress = min(Double(elapsedSeconds) / 60.0, 0.95)
        return progress
    }

    private func updatePhase() {
        for (time, phase) in phases.reversed() {
            if elapsedSeconds >= time {
                currentPhase = phase
                break
            }
        }
    }
}

// MARK: - Full Size Image View

struct FullSizeImageView: View {
    let imageData: Data
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Image Preview")
                    .font(.headline)
                    .foregroundStyle(.white)

                Spacer()

                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title2)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding()
            .background(.regularMaterial)

            // Image
            ScrollView([.horizontal, .vertical]) {
                if let nsImage = NSImage(data: imageData) {
                    Image(nsImage: nsImage)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .background(Color.black.opacity(0.8))
        }
        .frame(minWidth: 500, minHeight: 400)
    }
}

// MARK: - Feedback Buttons

struct FeedbackButtons: View {
    let currentRating: ChatMessage.FeedbackRating?
    let onFeedback: (ChatMessage.FeedbackRating, String?) -> Void

    @State private var showCorrectionField = false
    @State private var correctionText = ""
    @State private var showConfirmation = false

    var body: some View {
        HStack(spacing: 4) {
            // Thumbs up button
            Button(action: {
                onFeedback(.positive, nil)
                showConfirmation = true
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                    showConfirmation = false
                }
            }) {
                Image(systemName: currentRating == .positive ? "hand.thumbsup.fill" : "hand.thumbsup")
                    .font(.system(size: 10))
                    .foregroundStyle(currentRating == .positive ? .green : .secondary.opacity(0.6))
            }
            .buttonStyle(.plain)
            .disabled(currentRating != nil)

            // Thumbs down button
            Button(action: {
                if currentRating == nil {
                    showCorrectionField.toggle()
                }
            }) {
                Image(systemName: currentRating == .negative ? "hand.thumbsdown.fill" : "hand.thumbsdown")
                    .font(.system(size: 10))
                    .foregroundStyle(currentRating == .negative ? .red : .secondary.opacity(0.6))
            }
            .buttonStyle(.plain)
            .disabled(currentRating != nil)
            .popover(isPresented: $showCorrectionField, arrowEdge: .bottom) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("What should SAM have said?")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    TextField("Optional correction...", text: $correctionText)
                        .textFieldStyle(.plain)
                        .padding(8)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 6))
                        .frame(width: 200)

                    HStack {
                        Button("Cancel") {
                            showCorrectionField = false
                            correctionText = ""
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)
                        .font(.caption)

                        Spacer()

                        Button("Submit") {
                            let correction = correctionText.isEmpty ? nil : correctionText
                            onFeedback(.negative, correction)
                            showCorrectionField = false
                            correctionText = ""
                            showConfirmation = true
                            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                showConfirmation = false
                            }
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.cyan)
                        .font(.caption.weight(.medium))
                    }
                }
                .padding(12)
                .frame(width: 220)
            }

            // Confirmation indicator
            if showConfirmation {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 10))
                    .foregroundStyle(.green)
                    .transition(.scale.combined(with: .opacity))
            }
        }
        .animation(.easeInOut(duration: 0.2), value: showConfirmation)
    }
}

// MARK: - Roleplay View

struct RoleplayView: View {
    @EnvironmentObject var samState: SAMState
    @State private var selectedCharacter: String? = nil
    @State private var messageText = ""
    @State private var messages: [ChatMessage] = []
    @State private var isLoading = false

    let characters = [
        ("SAM", "brain.fill", "Your AI companion - cocky, flirty, loyal"),
        ("Custom", "person.fill.questionmark", "Create your own character"),
    ]

    var body: some View {
        HStack(spacing: 0) {
            // Character selector
            VStack(alignment: .leading, spacing: 16) {
                Text("Characters")
                    .font(.headline)
                    .foregroundStyle(.white)
                    .padding(.horizontal)

                ForEach(characters, id: \.0) { char in
                    CharacterCard(
                        name: char.0,
                        icon: char.1,
                        description: char.2,
                        isSelected: selectedCharacter == char.0
                    ) {
                        selectedCharacter = char.0
                        messages = [ChatMessage(role: .assistant, content: getGreeting(char.0))]
                    }
                }

                Spacer()
            }
            .frame(width: 200)
            .padding(.vertical)
            .background(.regularMaterial)

            // Chat area
            if selectedCharacter != nil {
                VStack(spacing: 0) {
                    // Messages
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(Array(messages.enumerated()), id: \.element.id) { index, message in
                                MessageBubble(message: message) { rating, correction in
                                    submitRoleplayFeedback(for: index, rating: rating, correction: correction)
                                }
                                .environmentObject(samState)
                            }

                            if isLoading {
                                HStack {
                                    ProgressView()
                                        .scaleEffect(0.8)
                                    Spacer()
                                }
                                .padding(.horizontal)
                            }
                        }
                        .padding()
                    }

                    // Input
                    HStack(spacing: 12) {
                        TextField("Your message...", text: $messageText)
                            .textFieldStyle(.plain)
                            .padding(12)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                            .onSubmit {
                                sendRoleplayMessage()
                            }

                        Button(action: sendRoleplayMessage) {
                            Image(systemName: "arrow.up.circle.fill")
                                .font(.system(size: 28))
                                .foregroundStyle(.purple)
                        }
                        .buttonStyle(.plain)
                        .disabled(messageText.isEmpty || isLoading)
                    }
                    .padding()
                    .background(.regularMaterial)
                }
            } else {
                VStack {
                    Image(systemName: "theatermasks")
                        .font(.system(size: 48))
                        .foregroundStyle(.secondary)
                    Text("Select a character to begin")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }

    func getGreeting(_ character: String) -> String {
        switch character {
        case "SAM":
            return "Hey gorgeous. Ready to have some fun?"
        default:
            return "Hello. How can I help you today?"
        }
    }

    func sendRoleplayMessage() {
        guard !messageText.isEmpty, let character = selectedCharacter else { return }

        let userMessage = ChatMessage(role: .user, content: messageText)
        messages.append(userMessage)
        let query = messageText
        messageText = ""
        isLoading = true

        Task {
            let response = await samState.roleplay(character: character, message: query)
            await MainActor.run {
                messages.append(ChatMessage(role: .assistant, content: response))
                // Auto-speak response if voice is enabled (Phase 6.1)
                if samState.voiceEnabled {
                    Task { await samState.speak(text: response) }
                }
                isLoading = false
            }
        }
    }

    func submitRoleplayFeedback(for index: Int, rating: ChatMessage.FeedbackRating, correction: String?) {
        guard index < messages.count else { return }

        // Update local state
        messages[index].feedbackRating = rating

        // Submit to API
        let message = messages[index]
        Task {
            await samState.submitFeedback(
                responseId: message.id.uuidString,
                responseContent: message.content,
                rating: rating == .positive ? "positive" : "negative",
                correction: correction
            )
        }
    }
}

struct CharacterCard: View {
    let name: String
    let icon: String
    let description: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundStyle(isSelected ? .purple : .secondary)
                    .frame(width: 32)

                VStack(alignment: .leading, spacing: 2) {
                    Text(name)
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text(description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                Spacer()
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isSelected ? Color.purple.opacity(0.2) : Color.clear)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? Color.purple.opacity(0.5) : Color.clear, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 8)
    }
}

// MARK: - Approval Queue View

struct ApprovalQueueView: View {
    @EnvironmentObject var samState: SAMState

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Pending Actions")
                    .font(.headline)
                    .foregroundStyle(.white)

                Spacer()

                if samState.isLoadingApprovals {
                    ProgressView()
                        .scaleEffect(0.7)
                }

                Button(action: {
                    Task { await samState.fetchPendingApprovals() }
                }) {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 14))
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }
            .padding()
            .background(.regularMaterial)

            // Content
            if let error = samState.approvalError {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundStyle(.orange)
                    Text(error)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .padding()
            } else if samState.pendingApprovals.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "checkmark.shield.fill")
                        .font(.system(size: 48))
                        .foregroundStyle(.green.opacity(0.7))
                    Text("No Pending Actions")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                    Text("SAM will request approval here before taking autonomous actions")
                        .font(.caption)
                        .foregroundStyle(.secondary.opacity(0.7))
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .padding()
            } else {
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(samState.pendingApprovals) { item in
                            ApprovalItemCard(item: item)
                                .environmentObject(samState)
                        }
                    }
                    .padding()
                }
            }
        }
    }
}

struct ApprovalItemCard: View {
    let item: ApprovalItem
    @EnvironmentObject var samState: SAMState
    @State private var isExpanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header with risk badge
            HStack {
                // Risk level badge
                Text(item.riskLevel.rawValue.uppercased())
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(riskColor(item.riskLevel)))

                Spacer()

                // Time remaining
                Text(item.timeRemainingFormatted)
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.7))
            }

            // Command
            Text(item.command)
                .font(.system(.body, design: .monospaced))
                .foregroundStyle(.cyan)
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.black.opacity(0.3))
                )

            // Reasoning
            Text(item.reasoning)
                .font(.caption)
                .foregroundStyle(.secondary)

            // Actions
            HStack(spacing: 12) {
                Button(action: {
                    Task { await samState.approveItem(id: item.id) }
                }) {
                    HStack(spacing: 4) {
                        Image(systemName: "checkmark")
                        Text("Approve")
                    }
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Capsule().fill(Color.green))
                }
                .buttonStyle(.plain)

                Button(action: {
                    Task { await samState.rejectItem(id: item.id, reason: nil) }
                }) {
                    HStack(spacing: 4) {
                        Image(systemName: "xmark")
                        Text("Reject")
                    }
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Capsule().fill(Color.red.opacity(0.8)))
                }
                .buttonStyle(.plain)

                Spacer()
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.regularMaterial)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(riskColor(item.riskLevel).opacity(0.3), lineWidth: 1)
                )
        )
    }

    private func riskColor(_ risk: RiskLevel) -> Color {
        switch risk {
        case .safe: return .green
        case .moderate: return .yellow
        case .dangerous: return .orange
        case .blocked: return .red
        }
    }
}

// MARK: - Control View

struct ControlView: View {
    @EnvironmentObject var samState: SAMState

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Header
                HStack {
                    Image(systemName: "brain.fill")
                        .font(.system(size: 24))
                        .foregroundStyle(.cyan)

                    VStack(alignment: .leading) {
                        Text("SAM Services")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundStyle(.white)
                        Text("Manage background services")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    // Status badge
                    HStack(spacing: 6) {
                        Circle()
                            .fill(samState.isHealthy ? Color.green : Color.orange)
                            .frame(width: 8, height: 8)
                        Text(samState.isHealthy ? "Healthy" : "Degraded")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(.regularMaterial, in: Capsule())
                }
                .padding()

                // Services Grid
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                    ForEach(samState.services) { service in
                        ServiceCard(service: service)
                    }
                }
                .padding(.horizontal)

                // Resources
                ResourcesCard(resources: samState.resources)
                    .padding(.horizontal)

                // Quick Actions
                HStack(spacing: 12) {
                    ActionButton(title: "Start All", icon: "play.fill", color: .green) {
                        samState.startAll()
                    }
                    ActionButton(title: "Stop All", icon: "stop.fill", color: .red) {
                        samState.stopAll()
                    }
                    ActionButton(title: "Refresh", icon: "arrow.clockwise", color: .blue) {
                        samState.refresh()
                    }
                }
                .padding()
            }
            .padding(.vertical)
        }
    }
}

struct ActionButton: View {
    let title: String
    let icon: String
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                Text(title)
            }
            .font(.system(size: 13, weight: .medium))
            .foregroundStyle(.white)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(color.opacity(0.8), in: RoundedRectangle(cornerRadius: 8))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Code View

struct CodeView: View {
    @EnvironmentObject var samState: SAMState
    @State private var orchestratorStatus: String = "Checking..."

    var body: some View {
        VStack(spacing: 24) {
            // Header
            VStack(spacing: 8) {
                Image(systemName: "terminal.fill")
                    .font(.system(size: 48))
                    .foregroundStyle(.cyan)

                Text("Dual Claude Terminals")
                    .font(.title)
                    .fontWeight(.semibold)
                    .foregroundStyle(.white)

                Text("Two Claude instances working together - Builder & Reviewer")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.top, 40)

            // Status
            HStack(spacing: 16) {
                StatusPill(title: "Orchestrator", status: orchestratorStatus)
            }

            // Launch Button
            Button(action: launchDualTerminals) {
                HStack {
                    Image(systemName: "rectangle.split.2x1.fill")
                    Text("Launch Dual Terminals")
                }
                .font(.headline)
                .foregroundStyle(.white)
                .padding(.horizontal, 32)
                .padding(.vertical, 16)
                .background(
                    LinearGradient(
                        colors: [.cyan, .blue],
                        startPoint: .leading,
                        endPoint: .trailing
                    ),
                    in: RoundedRectangle(cornerRadius: 12)
                )
                .shadow(color: .cyan.opacity(0.4), radius: 8)
            }
            .buttonStyle(.plain)

            // Role descriptions
            HStack(spacing: 24) {
                RoleCard(
                    title: "Builder",
                    icon: "hammer.fill",
                    description: "Plans architecture, writes Swift/SwiftUI code",
                    color: .green
                )

                RoleCard(
                    title: "Reviewer",
                    icon: "eye.fill",
                    description: "Reviews code, catches bugs, suggests improvements",
                    color: .orange
                )
            }
            .padding(.horizontal, 40)

            Spacer()

            // Hint
            Text("Terminals coordinate via [HANDOFF:ROLE] signals")
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.bottom)
        }
        .onAppear {
            checkOrchestrator()
        }
    }

    func checkOrchestrator() {
        Task {
            let running = await samState.checkOrchestrator()
            await MainActor.run {
                orchestratorStatus = running ? "Running" : "Stopped"
            }
        }
    }

    func launchDualTerminals() {
        let script = "cd ~/ReverseLab/SAM/warp_tauri && ./sam_bridge.sh launch"
        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = ["-c", script]
        try? task.run()
    }
}

struct StatusPill: View {
    let title: String
    let status: String

    var isRunning: Bool {
        status == "Running"
    }

    var body: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(isRunning ? Color.green : Color.orange)
                .frame(width: 8, height: 8)
            Text(title)
                .foregroundStyle(.secondary)
            Text(status)
                .fontWeight(.medium)
                .foregroundStyle(isRunning ? .green : .orange)
        }
        .font(.caption)
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(.regularMaterial, in: Capsule())
    }
}

struct RoleCard: View {
    let title: String
    let icon: String
    let description: String
    let color: Color

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title)
                .foregroundStyle(color)

            Text(title)
                .font(.headline)
                .foregroundStyle(.white)

            Text(description)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(color.opacity(0.3), lineWidth: 1)
        )
    }
}

// MARK: - Shared Components

struct AnimatedGradientBackground: View {
    @State private var startPoint = UnitPoint(x: 0, y: 0)
    @State private var endPoint = UnitPoint(x: 1, y: 1)

    let timer = Timer.publish(every: 0.05, on: .main, in: .common).autoconnect()
    @State private var phase: Double = 0

    var body: some View {
        LinearGradient(
            colors: [
                Color(red: 0.06, green: 0.06, blue: 0.14),
                Color(red: 0.10, green: 0.08, blue: 0.22),
                Color(red: 0.14, green: 0.10, blue: 0.26),
                Color(red: 0.08, green: 0.12, blue: 0.20),
            ],
            startPoint: startPoint,
            endPoint: endPoint
        )
        .ignoresSafeArea()
        .onReceive(timer) { _ in
            // Increment phase slowly - full cycle in ~30 seconds
            phase += 0.003
            if phase > .pi * 2 { phase = 0 }

            // Smooth circular motion
            withAnimation(.linear(duration: 0.05)) {
                startPoint = UnitPoint(
                    x: 0.5 + cos(phase) * 0.5,
                    y: 0.5 + sin(phase) * 0.5
                )
                endPoint = UnitPoint(
                    x: 0.5 - cos(phase) * 0.5,
                    y: 0.5 - sin(phase) * 0.5
                )
            }
        }
    }
}

struct ServiceCard: View {
    let service: SAMService
    @EnvironmentObject var samState: SAMState
    @State private var isHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: service.icon)
                    .font(.title2)
                    .foregroundStyle(service.statusColor)

                Spacer()

                Text(service.status.rawValue.capitalized)
                    .font(.caption2)
                    .fontWeight(.medium)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(service.statusColor.opacity(0.2), in: Capsule())
                    .foregroundStyle(service.statusColor)
            }

            Text(service.name)
                .font(.headline)
                .foregroundStyle(.white)

            HStack(spacing: 8) {
                Button(action: {
                    if service.status == .running {
                        samState.stopService(service.id)
                    } else {
                        samState.startService(service.id)
                    }
                }) {
                    Label(
                        service.status == .running ? "Stop" : "Start",
                        systemImage: service.status == .running ? "stop.fill" : "play.fill"
                    )
                    .font(.caption)
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(service.status == .running ? .red : .green)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
                .shadow(color: isHovered ? service.statusColor.opacity(0.3) : .clear, radius: 10)
        )
        .scaleEffect(isHovered ? 1.02 : 1.0)
        .animation(.spring(response: 0.3), value: isHovered)
        .onHover { isHovered = $0 }
    }
}

struct ResourcesCard: View {
    let resources: ResourceStatus

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("System Resources")
                .font(.headline)
                .foregroundStyle(.white)

            // RAM
            ResourceBar(
                title: "RAM",
                icon: "memorychip",
                color: .cyan,
                value: resources.ramUsedPercent,
                label: "\(String(format: "%.1f", resources.ramAvailable))GB / \(String(format: "%.1f", resources.ramTotal))GB"
            )

            // CPU
            ResourceBar(
                title: "CPU",
                icon: "cpu",
                color: .purple,
                value: resources.cpuPercent / 100,
                label: "\(Int(resources.cpuPercent))%"
            )
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
        )
    }
}

struct ResourceBar: View {
    let title: String
    let icon: String
    let color: Color
    let value: Double
    let label: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(color)
                Text(title)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(label)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(.white.opacity(0.1))

                    RoundedRectangle(cornerRadius: 4)
                        .fill(color)
                        .frame(width: geo.size.width * min(value, 1.0))
                }
            }
            .frame(height: 8)
        }
    }
}

// MARK: - Voice View

struct VoiceView: View {
    @EnvironmentObject var samState: SAMState
    @State private var trainingStatus: String = "Ready"
    @State private var isTraining: Bool = false
    @State private var audioPath: String = ""

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Header
                HStack(spacing: 16) {
                    Image(systemName: "waveform.circle.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(.orange)

                    VStack(alignment: .leading) {
                        Text("Voice System")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundStyle(.white)
                        Text("Text-to-speech and voice training")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    // Status badge
                    HStack(spacing: 6) {
                        Circle()
                            .fill(samState.isSpeaking ? Color.orange : (samState.voiceAPIAvailable ? Color.green : Color.yellow))
                            .frame(width: 8, height: 8)
                        Text(samState.isSpeaking ? "Speaking" : (samState.voiceAPIAvailable ? "API Ready" : "System Voice"))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(.regularMaterial, in: Capsule())
                }
                .padding()

                // Voice Settings Section (Phase 6.1)
                VoiceSettingsView()
                    .environmentObject(samState)
                    .padding(.horizontal)

                // Voice Selection for Training
                VStack(alignment: .leading, spacing: 12) {
                    Text("Available Voices")
                        .font(.headline)
                        .foregroundStyle(.white)

                    ForEach(samState.availableVoices) { voice in
                        VoiceOptionCard(
                            id: voice.id,
                            name: voice.name,
                            description: voice.isCustom ? "Custom trained voice" : (voice.language ?? "System voice"),
                            isSelected: samState.selectedVoice == voice.id
                        ) {
                            withAnimation { samState.selectedVoice = voice.id }
                        }
                    }
                }
                .padding(.horizontal)

                // Training Section
                VStack(alignment: .leading, spacing: 16) {
                    Text("Train New Voice")
                        .font(.headline)
                        .foregroundStyle(.white)

                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Image(systemName: "folder.fill")
                                .foregroundStyle(.orange)
                            TextField("Path to audio files...", text: $audioPath)
                                .textFieldStyle(.plain)
                                .foregroundStyle(.white)
                        }
                        .padding()
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8))

                        Text("Supported: .wav, .mp3, .m4a (3-10 minutes of clean audio)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    HStack(spacing: 12) {
                        Button(action: startTraining) {
                            HStack {
                                if isTraining {
                                    ProgressView()
                                        .scaleEffect(0.8)
                                } else {
                                    Image(systemName: "waveform")
                                }
                                Text(isTraining ? "Training..." : "Start Training")
                            }
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 20)
                            .padding(.vertical, 12)
                            .background(
                                isTraining ? Color.gray : Color.orange,
                                in: RoundedRectangle(cornerRadius: 8)
                            )
                        }
                        .buttonStyle(.plain)
                        .disabled(isTraining || audioPath.isEmpty)

                        Button(action: openFilePicker) {
                            HStack {
                                Image(systemName: "folder.badge.plus")
                                Text("Browse")
                            }
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 20)
                            .padding(.vertical, 12)
                            .background(Color.blue.opacity(0.8), in: RoundedRectangle(cornerRadius: 8))
                        }
                        .buttonStyle(.plain)

                        Spacer()

                        // Training status
                        if isTraining {
                            HStack(spacing: 6) {
                                ProgressView()
                                    .scaleEffect(0.6)
                                Text(trainingStatus)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                .padding()
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
                .padding(.horizontal)

                Spacer()
            }
            .padding(.vertical)
        }
    }

    func startTraining() {
        isTraining = true
        trainingStatus = "Training..."

        let script = """
        cd ~/ReverseLab/SAM/warp_tauri/sam_brain && python3 voice_trainer.py train "\(audioPath)" --name custom_voice
        """
        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = ["-c", script]
        task.terminationHandler = { _ in
            DispatchQueue.main.async {
                isTraining = false
                trainingStatus = "Ready"
                // Refresh voices to pick up newly trained voice
                Task {
                    await samState.fetchVoices()
                }
            }
        }
        try? task.run()
    }

    func openFilePicker() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = true
        panel.canChooseFiles = true
        panel.allowedContentTypes = [.audio, .folder]
        if panel.runModal() == .OK {
            audioPath = panel.url?.path ?? ""
        }
    }
}

struct VoiceOptionCard: View {
    let id: String
    let name: String
    let description: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 16) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .font(.title2)
                    .foregroundStyle(isSelected ? .orange : .secondary)

                VStack(alignment: .leading, spacing: 4) {
                    Text(name)
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text(description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isSelected ? AnyShapeStyle(Color.orange.opacity(0.15)) : AnyShapeStyle(.regularMaterial))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isSelected ? Color.orange.opacity(0.5) : Color.clear, lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Voice Settings View (Phase 6.1)

struct VoiceSettingsView: View {
    @EnvironmentObject var samState: SAMState
    @State private var isTestingSpeech = false
    @State private var showingSettings = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header with toggle
            HStack {
                Image(systemName: "speaker.wave.3.fill")
                    .font(.title2)
                    .foregroundStyle(.orange)

                VStack(alignment: .leading, spacing: 2) {
                    Text("Voice Output")
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text(samState.voiceAPIAvailable ? "SAM Voice API" : "macOS System Voice")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Toggle("", isOn: $samState.voiceEnabled)
                    .toggleStyle(.switch)
                    .tint(.orange)
            }

            if samState.voiceEnabled {
                Divider()
                    .background(Color.white.opacity(0.1))

                // Voice Selection
                VStack(alignment: .leading, spacing: 8) {
                    Text("Voice")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    Menu {
                        ForEach(samState.availableVoices) { voice in
                            Button(action: { samState.selectedVoice = voice.id }) {
                                HStack {
                                    Text(voice.name)
                                    if voice.isCustom {
                                        Image(systemName: "star.fill")
                                    }
                                    if samState.selectedVoice == voice.id {
                                        Image(systemName: "checkmark")
                                    }
                                }
                            }
                        }
                    } label: {
                        HStack {
                            Text(selectedVoiceName)
                                .foregroundStyle(.white)
                            Spacer()
                            Image(systemName: "chevron.up.chevron.down")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .padding(10)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8))
                    }
                    .menuStyle(.borderlessButton)
                }

                // Speed Slider
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Speed")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(String(format: "%.1fx", samState.voiceSpeed))
                            .font(.caption)
                            .foregroundStyle(.orange)
                            .monospacedDigit()
                    }

                    HStack(spacing: 8) {
                        Image(systemName: "tortoise.fill")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Slider(value: $samState.voiceSpeed, in: 0.5...2.0, step: 0.1)
                            .tint(.orange)

                        Image(systemName: "hare.fill")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                // Pitch Slider
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Pitch")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(String(format: "%.1fx", samState.voicePitch))
                            .font(.caption)
                            .foregroundStyle(.orange)
                            .monospacedDigit()
                    }

                    HStack(spacing: 8) {
                        Image(systemName: "arrow.down")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Slider(value: $samState.voicePitch, in: 0.5...2.0, step: 0.1)
                            .tint(.orange)

                        Image(systemName: "arrow.up")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Divider()
                    .background(Color.white.opacity(0.1))

                // Test Voice Button
                HStack(spacing: 12) {
                    Button(action: testVoice) {
                        HStack(spacing: 6) {
                            if isTestingSpeech {
                                ProgressView()
                                    .scaleEffect(0.7)
                            } else {
                                Image(systemName: "play.fill")
                            }
                            Text(isTestingSpeech ? "Speaking..." : "Test Voice")
                        }
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(
                            isTestingSpeech ? Color.gray : Color.orange,
                            in: RoundedRectangle(cornerRadius: 8)
                        )
                    }
                    .buttonStyle(.plain)
                    .disabled(isTestingSpeech)

                    if samState.isSpeaking {
                        Button(action: stopSpeaking) {
                            HStack(spacing: 6) {
                                Image(systemName: "stop.fill")
                                Text("Stop")
                            }
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                            .background(Color.red.opacity(0.8), in: RoundedRectangle(cornerRadius: 8))
                        }
                        .buttonStyle(.plain)
                    }

                    Spacer()

                    // Refresh voices button
                    Button(action: refreshVoices) {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                    .help("Refresh available voices")
                }

                // API status indicator
                HStack(spacing: 6) {
                    Circle()
                        .fill(samState.voiceAPIAvailable ? Color.green : Color.orange)
                        .frame(width: 6, height: 6)
                    Text(samState.voiceAPIAvailable ? "Voice API Connected" : "Using System Fallback")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
        )
    }

    private var selectedVoiceName: String {
        samState.availableVoices.first { $0.id == samState.selectedVoice }?.name ?? samState.selectedVoice
    }

    private func testVoice() {
        isTestingSpeech = true
        Task {
            await samState.speak(text: "Hey there, gorgeous. SAM here, ready to assist.")
            await MainActor.run {
                isTestingSpeech = false
            }
        }
    }

    private func stopSpeaking() {
        Task {
            await samState.stopSpeaking()
        }
    }

    private func refreshVoices() {
        Task {
            await samState.fetchVoices()
        }
    }
}

// MARK: - Speaker Button for Messages (Phase 6.1)

struct MessageSpeakerButton: View {
    let text: String
    @EnvironmentObject var samState: SAMState
    @State private var isSpeaking = false

    var body: some View {
        Button(action: toggleSpeaking) {
            ZStack {
                if isSpeaking {
                    // Animated speaking indicator
                    SpeakingWaveform()
                        .frame(width: 16, height: 12)
                } else {
                    Image(systemName: "speaker.wave.2")
                        .font(.system(size: 10))
                }
            }
            .foregroundStyle(isSpeaking ? .orange : .secondary.opacity(0.6))
            .frame(width: 20, height: 20)
        }
        .buttonStyle(.plain)
        .help(isSpeaking ? "Stop speaking" : "Speak this response")
        .opacity(samState.voiceEnabled ? 1.0 : 0.3)
        .disabled(!samState.voiceEnabled)
    }

    private func toggleSpeaking() {
        if isSpeaking {
            Task {
                await samState.stopSpeaking()
                await MainActor.run { isSpeaking = false }
            }
        } else {
            isSpeaking = true
            Task {
                await samState.speak(text: text)
                await MainActor.run { isSpeaking = false }
            }
        }
    }
}

// MARK: - Speaking Waveform Animation

struct SpeakingWaveform: View {
    @State private var animating = false

    var body: some View {
        HStack(spacing: 2) {
            ForEach(0..<3, id: \.self) { index in
                RoundedRectangle(cornerRadius: 1)
                    .fill(Color.orange)
                    .frame(width: 3)
                    .scaleEffect(y: animating ? 1.0 : 0.4, anchor: .center)
                    .animation(
                        Animation
                            .easeInOut(duration: 0.4)
                            .repeatForever(autoreverses: true)
                            .delay(Double(index) * 0.15),
                        value: animating
                    )
            }
        }
        .onAppear { animating = true }
    }
}

// MenuBarView removed - using simple WindowGroup now

#Preview {
    ContentView()
        .environmentObject(SAMState())
}
