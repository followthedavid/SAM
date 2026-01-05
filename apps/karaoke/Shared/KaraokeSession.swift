import Foundation
import MultipeerConnectivity

/// Shared protocol for iOS <-> tvOS karaoke communication
/// Uses MultipeerConnectivity for low-latency local network streaming

// MARK: - Message Types

enum KaraokeMessageType: String, Codable {
    case audioData          // Mic audio samples from iOS
    case playRequest        // iOS requests song playback
    case pauseRequest       // iOS requests pause
    case stopRequest        // iOS requests stop
    case syncLyrics         // tvOS sends current lyric position
    case songList           // tvOS sends available songs
    case nowPlaying         // tvOS sends current song info
    case micConnected       // iOS mic is connected
    case micDisconnected    // iOS mic disconnected
}

struct KaraokeMessage: Codable {
    let type: KaraokeMessageType
    let payload: Data?
    let timestamp: TimeInterval

    init(type: KaraokeMessageType, payload: Data? = nil) {
        self.type = type
        self.payload = payload
        self.timestamp = Date().timeIntervalSince1970
    }
}

// MARK: - Song Metadata

struct KaraokeSong: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let artist: String
    let album: String?
    let duration: TimeInterval
    let hasLyrics: Bool
    let videoPath: String

    var displayName: String {
        "\(artist) - \(title)"
    }
}

// MARK: - Session Manager

class KaraokeSessionManager: NSObject, ObservableObject {

    static let serviceType = "sam-karaoke"

    let peerID: MCPeerID
    var session: MCSession!

    @Published var connectedPeers: [MCPeerID] = []
    @Published var isConnected: Bool = false

    // Callbacks
    var onMessageReceived: ((KaraokeMessage, MCPeerID) -> Void)?
    var onAudioReceived: ((Data, MCPeerID) -> Void)?

    init(displayName: String) {
        self.peerID = MCPeerID(displayName: displayName)
        super.init()

        self.session = MCSession(
            peer: peerID,
            securityIdentity: nil,
            encryptionPreference: .none  // Low latency for audio
        )
        self.session.delegate = self
    }

    func send(_ message: KaraokeMessage, to peers: [MCPeerID]? = nil) {
        let targets = peers ?? session.connectedPeers
        guard !targets.isEmpty else { return }

        do {
            let data = try JSONEncoder().encode(message)
            try session.send(data, toPeers: targets, with: .reliable)
        } catch {
            print("Send error: \(error)")
        }
    }

    func sendAudio(_ audioData: Data, to peers: [MCPeerID]? = nil) {
        let targets = peers ?? session.connectedPeers
        guard !targets.isEmpty else { return }

        // Use unreliable for lower latency audio streaming
        do {
            try session.send(audioData, toPeers: targets, with: .unreliable)
        } catch {
            // Audio drops are acceptable
        }
    }

    func disconnect() {
        session.disconnect()
    }
}

// MARK: - MCSessionDelegate

extension KaraokeSessionManager: MCSessionDelegate {

    func session(_ session: MCSession, peer peerID: MCPeerID, didChange state: MCSessionState) {
        DispatchQueue.main.async {
            self.connectedPeers = session.connectedPeers
            self.isConnected = !session.connectedPeers.isEmpty

            switch state {
            case .connected:
                print("Connected to: \(peerID.displayName)")
            case .connecting:
                print("Connecting to: \(peerID.displayName)")
            case .notConnected:
                print("Disconnected from: \(peerID.displayName)")
            @unknown default:
                break
            }
        }
    }

    func session(_ session: MCSession, didReceive data: Data, fromPeer peerID: MCPeerID) {
        // Try to decode as KaraokeMessage first
        if let message = try? JSONDecoder().decode(KaraokeMessage.self, from: data) {
            DispatchQueue.main.async {
                self.onMessageReceived?(message, peerID)
            }
        } else {
            // Assume it's raw audio data
            onAudioReceived?(data, peerID)
        }
    }

    func session(_ session: MCSession, didReceive stream: InputStream, withName streamName: String, fromPeer peerID: MCPeerID) {
        // Not used - we send discrete audio packets
    }

    func session(_ session: MCSession, didStartReceivingResourceWithName resourceName: String, fromPeer peerID: MCPeerID, with progress: Progress) {}

    func session(_ session: MCSession, didFinishReceivingResourceWithName resourceName: String, fromPeer peerID: MCPeerID, at localURL: URL?, withError error: Error?) {}
}

// MARK: - Audio Format

struct KaraokeAudioFormat {
    static let sampleRate: Double = 44100
    static let channels: UInt32 = 1  // Mono mic
    static let bitsPerSample: UInt32 = 16
    static let bufferSize: Int = 4096  // ~93ms at 44.1kHz
}
