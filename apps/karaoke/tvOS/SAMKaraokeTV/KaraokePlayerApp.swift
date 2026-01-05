import SwiftUI
import MultipeerConnectivity
import AVKit

@main
struct KaraokePlayerApp: App {
    var body: some Scene {
        WindowGroup {
            MainPlayerView()
        }
    }
}

// MARK: - Main Player View

struct MainPlayerView: View {
    @StateObject private var viewModel = KaraokePlayerViewModel()

    var body: some View {
        ZStack {
            // Background
            Color.black.ignoresSafeArea()

            if viewModel.isPlaying, let player = viewModel.videoPlayer {
                // Video Player (karaoke video with lyrics)
                VideoPlayer(player: player)
                    .ignoresSafeArea()

                // Mic level overlay
                VStack {
                    Spacer()
                    HStack {
                        MicIndicatorView(
                            isConnected: viewModel.micConnected,
                            level: viewModel.micLevel
                        )
                        Spacer()
                    }
                    .padding(40)
                }
            } else {
                // Idle/Browse State
                IdleView(
                    isConnected: viewModel.isConnected,
                    connectedDevice: viewModel.connectedDeviceName,
                    songList: viewModel.songList,
                    onSelectSong: viewModel.playSong
                )
            }

            // Connection waiting overlay
            if !viewModel.isConnected {
                WaitingForConnectionView()
            }
        }
        .onAppear {
            viewModel.startAdvertising()
        }
    }
}

// MARK: - Waiting View

struct WaitingForConnectionView: View {
    @State private var rotation: Double = 0

    var body: some View {
        VStack(spacing: 30) {
            Image(systemName: "antenna.radiowaves.left.and.right")
                .font(.system(size: 80))
                .foregroundColor(.blue)
                .rotationEffect(.degrees(rotation))
                .animation(
                    Animation.easeInOut(duration: 2).repeatForever(autoreverses: true),
                    value: rotation
                )
                .onAppear { rotation = 10 }

            Text("SAM Karaoke")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("Open the SAM Karaoke app on your iPhone to connect")
                .font(.title3)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(60)
        .background(Color.black.opacity(0.8))
        .cornerRadius(30)
    }
}

// MARK: - Idle View (Song Browser)

struct IdleView: View {
    let isConnected: Bool
    let connectedDevice: String?
    let songList: [KaraokeSong]
    let onSelectSong: (KaraokeSong) -> Void

    var body: some View {
        VStack(spacing: 40) {
            // Header
            HStack {
                VStack(alignment: .leading) {
                    Text("SAM Karaoke")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    if let device = connectedDevice {
                        HStack {
                            Circle()
                                .fill(Color.green)
                                .frame(width: 10, height: 10)
                            Text("\(device) connected")
                                .font(.title3)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                Spacer()
            }
            .padding(.horizontal, 60)

            // Song Grid
            if songList.isEmpty {
                VStack(spacing: 20) {
                    Image(systemName: "music.note.list")
                        .font(.system(size: 60))
                        .foregroundColor(.secondary)
                    Text("No karaoke songs found")
                        .font(.title2)
                        .foregroundColor(.secondary)
                    Text("Generate karaoke videos using SAM and place them in the library folder")
                        .font(.body)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 30) {
                        ForEach(songList) { song in
                            SongCardView(song: song) {
                                onSelectSong(song)
                            }
                        }
                    }
                    .padding(.horizontal, 60)
                }
            }
        }
        .padding(.vertical, 40)
    }
}

// MARK: - Song Card

struct SongCardView: View {
    let song: KaraokeSong
    let onTap: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 12) {
                // Album art placeholder
                ZStack {
                    RoundedRectangle(cornerRadius: 12)
                        .fill(LinearGradient(
                            colors: [.purple, .blue],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ))

                    Image(systemName: "music.mic")
                        .font(.system(size: 40))
                        .foregroundColor(.white.opacity(0.8))
                }
                .aspectRatio(1, contentMode: .fit)

                VStack(alignment: .leading, spacing: 4) {
                    Text(song.title)
                        .font(.headline)
                        .lineLimit(1)

                    Text(song.artist)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
            }
            .padding()
            .background(isFocused ? Color.white.opacity(0.1) : Color.clear)
            .cornerRadius(16)
            .scaleEffect(isFocused ? 1.05 : 1.0)
            .animation(.easeOut(duration: 0.15), value: isFocused)
        }
        .buttonStyle(PlainButtonStyle())
        .focused($isFocused)
    }
}

// MARK: - Mic Indicator

struct MicIndicatorView: View {
    let isConnected: Bool
    let level: Float

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: isConnected ? "mic.fill" : "mic.slash")
                .font(.title2)
                .foregroundColor(isConnected ? .green : .gray)

            // Level bars
            if isConnected {
                HStack(spacing: 3) {
                    ForEach(0..<10, id: \.self) { i in
                        RoundedRectangle(cornerRadius: 2)
                            .fill(Float(i) / 10.0 < level ? Color.green : Color.gray.opacity(0.3))
                            .frame(width: 6, height: 20)
                    }
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .background(Color.black.opacity(0.6))
        .cornerRadius(25)
    }
}

// MARK: - View Model

class KaraokePlayerViewModel: NSObject, ObservableObject {

    @Published var isConnected = false
    @Published var connectedDeviceName: String?
    @Published var micConnected = false
    @Published var micLevel: Float = 0.0
    @Published var isPlaying = false
    @Published var currentSong: KaraokeSong?
    @Published var songList: [KaraokeSong] = []
    @Published var videoPlayer: AVPlayer?

    private var sessionManager: KaraokeSessionManager!
    private var audioMixer: AudioMixer!
    private var advertiser: MCNearbyServiceAdvertiser?

    // Library path (configurable)
    private let libraryPath = "/Users/Shared/SAMKaraoke"

    override init() {
        super.init()

        sessionManager = KaraokeSessionManager(displayName: "Apple TV")
        audioMixer = AudioMixer()

        setupCallbacks()
        loadSongLibrary()
    }

    private func setupCallbacks() {
        sessionManager.$isConnected
            .receive(on: DispatchQueue.main)
            .assign(to: &$isConnected)

        sessionManager.$connectedPeers
            .receive(on: DispatchQueue.main)
            .map { $0.first?.displayName }
            .assign(to: &$connectedDeviceName)

        audioMixer.$micLevel
            .receive(on: DispatchQueue.main)
            .assign(to: &$micLevel)

        // Handle incoming messages
        sessionManager.onMessageReceived = { [weak self] message, peer in
            self?.handleMessage(message, from: peer)
        }

        // Handle incoming audio
        sessionManager.onAudioReceived = { [weak self] data, _ in
            self?.audioMixer.receiveMicAudio(data)
        }
    }

    func startAdvertising() {
        advertiser = MCNearbyServiceAdvertiser(
            peer: sessionManager.peerID,
            discoveryInfo: nil,
            serviceType: KaraokeSessionManager.serviceType
        )
        advertiser?.delegate = self
        advertiser?.startAdvertisingPeer()
        print("Advertising for iOS devices...")
    }

    // MARK: - Song Library

    private func loadSongLibrary() {
        let fileManager = FileManager.default
        let libraryURL = URL(fileURLWithPath: libraryPath)

        guard fileManager.fileExists(atPath: libraryPath) else {
            print("Library path not found: \(libraryPath)")
            // Create sample songs for demo
            songList = [
                KaraokeSong(id: "1", title: "Toxic", artist: "Britney Spears", album: "In the Zone", duration: 198, hasLyrics: true, videoPath: ""),
                KaraokeSong(id: "2", title: "Sexy Boy", artist: "Air", album: "Moon Safari", duration: 312, hasLyrics: true, videoPath: "")
            ]
            return
        }

        do {
            let files = try fileManager.contentsOfDirectory(at: libraryURL, includingPropertiesForKeys: nil)
            songList = files.compactMap { url -> KaraokeSong? in
                guard url.pathExtension == "mp4" else { return nil }

                let filename = url.deletingPathExtension().lastPathComponent
                // Parse "Artist - Title (Karaoke).mp4"
                let parts = filename.replacingOccurrences(of: " (Karaoke)", with: "")
                    .components(separatedBy: " - ")

                guard parts.count >= 2 else { return nil }

                return KaraokeSong(
                    id: url.path,
                    title: parts[1],
                    artist: parts[0],
                    album: nil,
                    duration: 0,
                    hasLyrics: true,
                    videoPath: url.path
                )
            }
            print("Loaded \(songList.count) songs")
        } catch {
            print("Failed to load library: \(error)")
        }
    }

    // MARK: - Playback

    func playSong(_ song: KaraokeSong) {
        currentSong = song

        let videoURL: URL
        if song.videoPath.isEmpty {
            // Demo mode - no actual file
            print("Demo mode: would play \(song.displayName)")
            return
        } else {
            videoURL = URL(fileURLWithPath: song.videoPath)
        }

        // Create video player
        videoPlayer = AVPlayer(url: videoURL)
        videoPlayer?.play()
        isPlaying = true

        // Start audio mixer
        audioMixer.start()

        // Notify iOS
        if let data = try? JSONEncoder().encode(song) {
            sessionManager.send(KaraokeMessage(type: .nowPlaying, payload: data))
        }
    }

    func stopPlayback() {
        videoPlayer?.pause()
        videoPlayer = nil
        isPlaying = false
        audioMixer.stop()
    }

    // MARK: - Message Handling

    private func handleMessage(_ message: KaraokeMessage, from peer: MCPeerID) {
        switch message.type {
        case .playRequest:
            if let data = message.payload,
               let song = try? JSONDecoder().decode(KaraokeSong.self, from: data) {
                playSong(song)
            }

        case .pauseRequest:
            videoPlayer?.pause()
            isPlaying = false

        case .stopRequest:
            stopPlayback()

        case .micConnected:
            micConnected = true

        case .micDisconnected:
            micConnected = false

        default:
            break
        }
    }

    // Send song list to connected iOS device
    private func sendSongList(to peer: MCPeerID) {
        if let data = try? JSONEncoder().encode(songList) {
            sessionManager.send(KaraokeMessage(type: .songList, payload: data), to: [peer])
        }
    }
}

// MARK: - Advertiser Delegate

extension KaraokePlayerViewModel: MCNearbyServiceAdvertiserDelegate {

    func advertiser(_ advertiser: MCNearbyServiceAdvertiser, didReceiveInvitationFromPeer peerID: MCPeerID, withContext context: Data?, invitationHandler: @escaping (Bool, MCSession?) -> Void) {
        print("Received invitation from: \(peerID.displayName)")
        invitationHandler(true, sessionManager.session)

        // Send song list after connection
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
            self?.sendSongList(to: peerID)
        }
    }

    func advertiser(_ advertiser: MCNearbyServiceAdvertiser, didNotStartAdvertisingPeer error: Error) {
        print("Failed to advertise: \(error)")
    }
}
