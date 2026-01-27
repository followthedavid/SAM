// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SAMControlCenter",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "SAMControlCenter", targets: ["SAMControlCenter"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "SAMControlCenter",
            dependencies: [],
            path: "Sources"
        )
    ]
)
