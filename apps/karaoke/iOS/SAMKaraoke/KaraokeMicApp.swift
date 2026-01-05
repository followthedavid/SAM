import SwiftUI
import MultipeerConnectivity

@main
struct KaraokeMicApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

// MARK: - Main Content View

struct ContentView: View {
    @StateObject private var viewModel = KaraokeMicViewModel()

    var body: some View {
        NavigationView {
            VStack(spacing: 30) {

                // Connection Status
                ConnectionStatusView(isConnected: viewModel.isConnected, peerName: viewModel.connectedTVName)

                Spacer()

                // Microphone Control
                MicrophoneView(
                    isCapturing: viewModel.isCapturing,
                    micLevel: viewModel.micLevel,
                    onToggle: viewModel.toggleMicrophone
                )

                Spacer()

                // Now Playing (if connected)
                if viewModel.isConnected {
                    NowPlayingView(song: viewModel.currentSong)
                }

                // Song List
                if viewModel.isConnected && !viewModel.songList.isEmpty {
                    SongListView(songs: viewModel.songList, onSelect: viewModel.requestSong)
                }

                Spacer()
            }
            .padding()
            .navigationTitle("SAM Karaoke")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: viewModel.startBrowsing) {
                        Image(systemName: "antenna.radiowaves.left.and.right")
                    }
                }
            }
            .onAppear {
                viewModel.startBrowsing()
            }
        }
    }
}

// MARK: - Connection Status

struct ConnectionStatusView: View {
    let isConnected: Bool
    let peerName: String?

    var body: some View {
        HStack {
            Circle()
                .fill(isConnected ? Color.green : Color.red)
                .frame(width: 12, height: 12)

            if isConnected, let name = peerName {
                Text("Connected to \(name)")
                    .font(.subheadline)
            } else {
                Text("Searching for Apple TV...")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Color(.systemGray6))
        .cornerRadius(20)
    }
}

// MARK: - Microphone View

struct MicrophoneView: View {
    let isCapturing: Bool
    let micLevel: Float
    let onToggle: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            // Mic button with level indicator
            ZStack {
                // Level ring
                Circle()
                    .stroke(Color.blue.opacity(0.3), lineWidth: 8)
                    .frame(width: 150, height: 150)

                Circle()
                    .trim(from: 0, to: CGFloat(micLevel))
                    .stroke(Color.blue, lineWidth: 8)
                    .frame(width: 150, height: 150)
                    .rotationEffect(.degrees(-90))
                    .animation(.easeOut(duration: 0.1), value: micLevel)

                // Mic button
                Button(action: onToggle) {
                    ZStack {
                        Circle()
                            .fill(isCapturing ? Color.red : Color.blue)
                            .frame(width: 120, height: 120)

                        Image(systemName: isCapturing ? "mic.fill" : "mic.slash.fill")
                            .font(.system(size: 50))
                            .foregroundColor(.white)
                    }
                }
            }

            Text(isCapturing ? "Tap to Mute" : "Tap to Unmute")
                .font(.headline)
                .foregroundColor(.secondary)
        }
    }
}

// MARK: - Now Playing

struct NowPlayingView: View {
    let song: KaraokeSong?

    var body: some View {
        if let song = song {
            VStack(spacing: 8) {
                Text("Now Playing")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(song.title)
                    .font(.title2)
                    .fontWeight(.bold)
                Text(song.artist)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .padding()
            .frame(maxWidth: .infinity)
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
    }
}

// MARK: - Song List

struct SongListView: View {
    let songs: [KaraokeSong]
    let onSelect: (KaraokeSong) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Available Songs")
                .font(.headline)

            ScrollView {
                LazyVStack(spacing: 4) {
                    ForEach(songs) { song in
                        Button(action: { onSelect(song) }) {
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(song.title)
                                        .font(.body)
                                    Text(song.artist)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                Spacer()
                                Image(systemName: "play.circle")
                                    .foregroundColor(.blue)
                            }
                            .padding(.vertical, 8)
                        }
                        .buttonStyle(PlainButtonStyle())
                        Divider()
                    }
                }
            }
            .frame(maxHeight: 200)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - View Model

class KaraokeMicViewModel: NSObject, ObservableObject {

    @Published var isConnected = false
    @Published var connectedTVName: String?
    @Published var isCapturing = false
    @Published var micLevel: Float = 0.0
    @Published var currentSong: KaraokeSong?
    @Published var songList: [KaraokeSong] = []

    private var sessionManager: KaraokeSessionManager!
    private var micManager: MicrophoneManager!
    private var browser: MCNearbyServiceBrowser?

    override init() {
        super.init()

        sessionManager = KaraokeSessionManager(displayName: UIDevice.current.name)
        micManager = MicrophoneManager()

        setupCallbacks()
    }

    private func setupCallbacks() {
        // Audio captured -> send to TV
        micManager.onAudioCaptured = { [weak self] data in
            self?.sessionManager.sendAudio(data)
        }

        // Mic level updates
        micManager.$micLevel
            .receive(on: DispatchQueue.main)
            .assign(to: &$micLevel)

        micManager.$isCapturing
            .receive(on: DispatchQueue.main)
            .assign(to: &$isCapturing)

        // Session updates
        sessionManager.$isConnected
            .receive(on: DispatchQueue.main)
            .assign(to: &$isConnected)

        sessionManager.$connectedPeers
            .receive(on: DispatchQueue.main)
            .map { $0.first?.displayName }
            .assign(to: &$connectedTVName)

        // Messages from TV
        sessionManager.onMessageReceived = { [weak self] message, _ in
            self?.handleMessage(message)
        }
    }

    func startBrowsing() {
        browser = MCNearbyServiceBrowser(peer: sessionManager.peerID, serviceType: KaraokeSessionManager.serviceType)
        browser?.delegate = self
        browser?.startBrowsingForPeers()
        print("Browsing for Apple TV...")
    }

    func toggleMicrophone() {
        if isCapturing {
            micManager.stopCapturing()
            sessionManager.send(KaraokeMessage(type: .micDisconnected))
        } else {
            micManager.startCapturing()
            sessionManager.send(KaraokeMessage(type: .micConnected))
        }
    }

    func requestSong(_ song: KaraokeSong) {
        guard let data = try? JSONEncoder().encode(song) else { return }
        sessionManager.send(KaraokeMessage(type: .playRequest, payload: data))
    }

    private func handleMessage(_ message: KaraokeMessage) {
        switch message.type {
        case .songList:
            if let data = message.payload,
               let songs = try? JSONDecoder().decode([KaraokeSong].self, from: data) {
                songList = songs
            }
        case .nowPlaying:
            if let data = message.payload,
               let song = try? JSONDecoder().decode(KaraokeSong.self, from: data) {
                currentSong = song
            }
        default:
            break
        }
    }
}

// MARK: - Browser Delegate

extension KaraokeMicViewModel: MCNearbyServiceBrowserDelegate {

    func browser(_ browser: MCNearbyServiceBrowser, foundPeer peerID: MCPeerID, withDiscoveryInfo info: [String : String]?) {
        print("Found TV: \(peerID.displayName)")
        browser.invitePeer(peerID, to: sessionManager.session, withContext: nil, timeout: 30)
    }

    func browser(_ browser: MCNearbyServiceBrowser, lostPeer peerID: MCPeerID) {
        print("Lost TV: \(peerID.displayName)")
    }
}
