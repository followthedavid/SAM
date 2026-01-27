// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "FashionArchive",
    platforms: [
        .macOS(.v14),
        .iOS(.v17),
        .tvOS(.v17)
    ],
    products: [
        .library(
            name: "FashionArchive",
            targets: ["FashionArchive"]
        )
    ],
    targets: [
        .target(
            name: "FashionArchive",
            path: "Sources"
        )
    ]
)
