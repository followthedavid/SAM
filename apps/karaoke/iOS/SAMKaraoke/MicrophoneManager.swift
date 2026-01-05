import Foundation
import AVFoundation

/// Captures microphone audio and streams to tvOS
class MicrophoneManager: NSObject, ObservableObject {

    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?

    @Published var isCapturing = false
    @Published var micLevel: Float = 0.0
    @Published var permissionGranted = false

    var onAudioCaptured: ((Data) -> Void)?

    override init() {
        super.init()
        checkPermission()
    }

    func checkPermission() {
        switch AVAudioSession.sharedInstance().recordPermission {
        case .granted:
            permissionGranted = true
        case .denied:
            permissionGranted = false
        case .undetermined:
            AVAudioSession.sharedInstance().requestRecordPermission { [weak self] granted in
                DispatchQueue.main.async {
                    self?.permissionGranted = granted
                }
            }
        @unknown default:
            break
        }
    }

    func startCapturing() {
        guard permissionGranted else {
            print("Microphone permission not granted")
            return
        }

        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            try session.setActive(true)

            audioEngine = AVAudioEngine()
            inputNode = audioEngine?.inputNode

            guard let inputNode = inputNode else { return }

            let recordingFormat = inputNode.outputFormat(forBus: 0)

            // Install tap on input node
            inputNode.installTap(onBus: 0, bufferSize: UInt32(KaraokeAudioFormat.bufferSize), format: recordingFormat) { [weak self] buffer, time in
                self?.processAudioBuffer(buffer)
            }

            try audioEngine?.start()
            isCapturing = true
            print("Microphone capture started")

        } catch {
            print("Failed to start audio capture: \(error)")
        }
    }

    func stopCapturing() {
        inputNode?.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        inputNode = nil
        isCapturing = false
        print("Microphone capture stopped")
    }

    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        guard let channelData = buffer.floatChannelData else { return }

        let frames = buffer.frameLength
        let channels = buffer.format.channelCount

        // Calculate mic level for UI
        var sum: Float = 0
        for frame in 0..<Int(frames) {
            let sample = channelData[0][frame]
            sum += sample * sample
        }
        let rms = sqrt(sum / Float(frames))
        DispatchQueue.main.async {
            self.micLevel = min(1.0, rms * 5)  // Scale for visibility
        }

        // Convert to 16-bit PCM data for transmission
        let data = convertToData(buffer)
        onAudioCaptured?(data)
    }

    private func convertToData(_ buffer: AVAudioPCMBuffer) -> Data {
        guard let channelData = buffer.floatChannelData else { return Data() }

        let frames = Int(buffer.frameLength)
        var int16Data = [Int16](repeating: 0, count: frames)

        // Convert float samples to Int16
        for i in 0..<frames {
            let sample = channelData[0][i]
            let clipped = max(-1.0, min(1.0, sample))
            int16Data[i] = Int16(clipped * Float(Int16.max))
        }

        return Data(bytes: int16Data, count: frames * 2)
    }
}
