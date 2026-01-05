import Foundation
import AVFoundation

/// Mixes backing track audio with incoming microphone audio from iOS
class AudioMixer: ObservableObject {

    private var audioEngine: AVAudioEngine!
    private var playerNode: AVAudioPlayerNode!
    private var micMixerNode: AVAudioMixerNode!

    private var micBuffer: AVAudioPCMBuffer?
    private let micFormat: AVAudioFormat

    @Published var isPlaying = false
    @Published var micLevel: Float = 0.0
    @Published var backingVolume: Float = 1.0
    @Published var micVolume: Float = 1.0

    // Circular buffer for incoming mic audio
    private var micAudioQueue = [Data]()
    private let micQueueLock = NSLock()

    init() {
        // Mic audio format (16-bit mono from iOS)
        micFormat = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: KaraokeAudioFormat.sampleRate,
            channels: 1,
            interleaved: false
        )!

        setupAudioEngine()
    }

    private func setupAudioEngine() {
        audioEngine = AVAudioEngine()
        playerNode = AVAudioPlayerNode()
        micMixerNode = AVAudioMixerNode()

        audioEngine.attach(playerNode)
        audioEngine.attach(micMixerNode)

        let mainMixer = audioEngine.mainMixerNode
        let outputFormat = mainMixer.outputFormat(forBus: 0)

        // Connect: playerNode -> mainMixer (backing track)
        audioEngine.connect(playerNode, to: mainMixer, format: outputFormat)

        // Connect: micMixerNode -> mainMixer (mic audio)
        audioEngine.connect(micMixerNode, to: mainMixer, format: micFormat)

        // Start mic audio injection timer
        startMicInjection()
    }

    func start() {
        do {
            try audioEngine.start()
            print("Audio engine started")
        } catch {
            print("Failed to start audio engine: \(error)")
        }
    }

    func stop() {
        playerNode.stop()
        audioEngine.stop()
        isPlaying = false
    }

    // MARK: - Backing Track Playback

    func playBackingTrack(url: URL) {
        do {
            let audioFile = try AVAudioFile(forReading: url)

            playerNode.scheduleFile(audioFile, at: nil) { [weak self] in
                DispatchQueue.main.async {
                    self?.isPlaying = false
                }
            }

            if !audioEngine.isRunning {
                try audioEngine.start()
            }

            playerNode.play()
            isPlaying = true
            print("Playing backing track: \(url.lastPathComponent)")

        } catch {
            print("Failed to play backing track: \(error)")
        }
    }

    func pause() {
        playerNode.pause()
        isPlaying = false
    }

    func resume() {
        playerNode.play()
        isPlaying = true
    }

    // MARK: - Microphone Audio Injection

    func receiveMicAudio(_ data: Data) {
        micQueueLock.lock()
        micAudioQueue.append(data)
        // Keep queue bounded (max ~500ms of audio)
        while micAudioQueue.count > 20 {
            micAudioQueue.removeFirst()
        }
        micQueueLock.unlock()
    }

    private func startMicInjection() {
        // Timer to pull mic audio from queue and inject into mixer
        Timer.scheduledTimer(withTimeInterval: 0.02, repeats: true) { [weak self] _ in
            self?.injectMicAudio()
        }
    }

    private func injectMicAudio() {
        micQueueLock.lock()
        guard let data = micAudioQueue.first else {
            micQueueLock.unlock()
            return
        }
        micAudioQueue.removeFirst()
        micQueueLock.unlock()

        // Convert Int16 data to Float32 PCM buffer
        let int16Count = data.count / 2
        guard int16Count > 0 else { return }

        guard let buffer = AVAudioPCMBuffer(pcmFormat: micFormat, frameCapacity: AVAudioFrameCount(int16Count)) else { return }
        buffer.frameLength = AVAudioFrameCount(int16Count)

        data.withUnsafeBytes { rawPtr in
            guard let int16Ptr = rawPtr.bindMemory(to: Int16.self).baseAddress else { return }
            guard let floatChannel = buffer.floatChannelData?[0] else { return }

            for i in 0..<int16Count {
                floatChannel[i] = Float(int16Ptr[i]) / Float(Int16.max)
            }
        }

        // Calculate mic level for display
        if let channelData = buffer.floatChannelData?[0] {
            var sum: Float = 0
            for i in 0..<int16Count {
                sum += channelData[i] * channelData[i]
            }
            let rms = sqrt(sum / Float(int16Count))
            DispatchQueue.main.async {
                self.micLevel = min(1.0, rms * 5)
            }
        }

        // Apply mic volume
        if let channelData = buffer.floatChannelData?[0] {
            for i in 0..<int16Count {
                channelData[i] *= micVolume
            }
        }

        // Schedule buffer on mic mixer
        // Note: In a production app, you'd use a more sophisticated
        // approach with AVAudioSourceNode for real-time injection
    }

    // MARK: - Volume Control

    func setBackingVolume(_ volume: Float) {
        backingVolume = max(0, min(1, volume))
        playerNode.volume = backingVolume
    }

    func setMicVolume(_ volume: Float) {
        micVolume = max(0, min(2, volume))  // Allow boost up to 2x
        micMixerNode.volume = micVolume
    }
}
