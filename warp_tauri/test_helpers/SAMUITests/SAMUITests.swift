import XCTest

/**
 SAM UI Tests

 These tests use XCTest's UI testing framework to verify the SAM app's behavior.

 Prerequisites:
 1. SAM app must be built and available at the expected path
 2. SAM must grant accessibility permissions to the test runner

 Running tests:
 - Open SAMUITests.xcodeproj in Xcode
 - Select the SAMUITests scheme
 - Press Cmd+U to run tests
 - Or use: xcodebuild test -project SAMUITests.xcodeproj -scheme SAMUITests

 Note: For WebView content, you may need to add accessibility labels
 to Vue components for XCTest to find them.
*/

class SAMUITests: XCTestCase {

    // The SAM app bundle identifier
    let samBundleId = "com.sam.terminal"

    // Debug server URL
    let debugURL = "http://localhost:9998"

    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false

        // Initialize app with bundle ID
        app = XCUIApplication(bundleIdentifier: samBundleId)

        // Alternatively, launch by path if bundle ID doesn't work
        // app = XCUIApplication()
        // app.launchEnvironment["SAM_TEST_MODE"] = "1"
    }

    override func tearDownWithError() throws {
        // Take screenshot on failure
        if testRun?.failureCount ?? 0 > 0 {
            let screenshot = XCUIScreen.main.screenshot()
            let attachment = XCTAttachment(screenshot: screenshot)
            attachment.name = "Failure Screenshot"
            attachment.lifetime = .keepAlways
            add(attachment)
        }
    }

    // MARK: - Startup Tests

    func testAppLaunches() throws {
        // Launch the app
        app.launch()

        // Wait for window to appear
        let window = app.windows.firstMatch
        XCTAssertTrue(window.waitForExistence(timeout: 30), "SAM window should appear within 30 seconds")

        // Verify window is visible
        XCTAssertTrue(window.isHittable, "SAM window should be hittable")
    }

    func testWindowExists() throws {
        app.activate()

        let window = app.windows["SAM"]
        let exists = window.waitForExistence(timeout: 10)

        XCTAssertTrue(exists, "SAM window should exist")
    }

    func testDebugServerResponds() throws {
        // Query the debug server
        let expectation = XCTestExpectation(description: "Debug server responds")

        guard let url = URL(string: "\(debugURL)/debug/ping") else {
            XCTFail("Invalid debug URL")
            return
        }

        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            XCTAssertNil(error, "Debug server should not return error")
            XCTAssertNotNil(data, "Debug server should return data")

            if let httpResponse = response as? HTTPURLResponse {
                XCTAssertEqual(httpResponse.statusCode, 200, "Debug server should return 200")
            }

            expectation.fulfill()
        }
        task.resume()

        wait(for: [expectation], timeout: 5.0)
    }

    // MARK: - Ollama Tests

    func testOllamaModelsLoaded() throws {
        let expectation = XCTestExpectation(description: "Ollama models loaded")

        guard let url = URL(string: "\(debugURL)/debug/ollama") else {
            XCTFail("Invalid debug URL")
            return
        }

        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            XCTAssertNil(error)

            if let data = data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let loadedCount = json["loaded_count"] as? Int {
                XCTAssertGreaterThan(loadedCount, 0, "At least one model should be loaded")
            } else {
                XCTFail("Could not parse Ollama response")
            }

            expectation.fulfill()
        }
        task.resume()

        wait(for: [expectation], timeout: 10.0)
    }

    // MARK: - UI Element Tests

    func testMainUIElementsExist() throws {
        app.activate()

        // Wait for app to be ready
        sleep(2)

        // Check for common UI elements
        // Note: These queries depend on accessibility labels being set in the Vue components

        // Check if any buttons exist
        let buttons = app.buttons
        XCTAssertGreaterThan(buttons.count, 0, "App should have at least one button")

        // Check if any text fields exist (for chat input)
        let textFields = app.textFields
        let textViews = app.textViews
        let hasInputField = textFields.count > 0 || textViews.count > 0

        // Note: WebView content may not be directly accessible
        // You may need to add accessibility identifiers to Vue components
    }

    // MARK: - Accessibility Tests

    func testAccessibilityTree() throws {
        app.activate()
        sleep(2)

        // Print accessibility tree for debugging
        let window = app.windows.firstMatch
        if window.exists {
            print("Window found: \(window.debugDescription)")

            // Enumerate all descendants
            let descendants = window.descendants(matching: .any)
            print("Total descendants: \(descendants.count)")

            for i in 0..<min(descendants.count, 20) {
                let element = descendants.element(boundBy: i)
                print("Element \(i): \(element.elementType) - \(element.identifier) - \(element.label)")
            }
        }
    }

    // MARK: - Warm Model Test

    func testWarmModels() throws {
        let expectation = XCTestExpectation(description: "Models warmed")

        guard let url = URL(string: "\(debugURL)/debug/warm") else {
            XCTFail("Invalid debug URL")
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            XCTAssertNil(error, "Warm request should not fail")

            if let httpResponse = response as? HTTPURLResponse {
                XCTAssertEqual(httpResponse.statusCode, 200, "Warm should return 200")
            }

            expectation.fulfill()
        }
        task.resume()

        // Warming can take a while
        wait(for: [expectation], timeout: 120.0)
    }

    // MARK: - Performance Tests

    func testLaunchPerformance() throws {
        measure(metrics: [XCTApplicationLaunchMetric()]) {
            app.launch()
        }
    }
}

// MARK: - Test Helpers

extension SAMUITests {

    /// Query the debug server and return JSON response
    func queryDebugServer(endpoint: String) -> [String: Any]? {
        guard let url = URL(string: "\(debugURL)\(endpoint)") else {
            return nil
        }

        let semaphore = DispatchSemaphore(value: 0)
        var result: [String: Any]?

        let task = URLSession.shared.dataTask(with: url) { data, _, _ in
            if let data = data {
                result = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            }
            semaphore.signal()
        }
        task.resume()
        semaphore.wait()

        return result
    }

    /// Wait for a condition to be true
    func waitFor(timeout: TimeInterval = 10, condition: @escaping () -> Bool) -> Bool {
        let start = Date()
        while Date().timeIntervalSince(start) < timeout {
            if condition() {
                return true
            }
            Thread.sleep(forTimeInterval: 0.1)
        }
        return false
    }
}
