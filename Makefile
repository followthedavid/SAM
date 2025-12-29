.PHONY: test test-rust test-integration test-ui build-all ci generate-longscroll
.PHONY: test-integration-malformed test-integration-partialutf8 test-integration-longscroll
.PHONY: test-integration-overlapping test-integration-cjk test-integration-partialescape

# Run all tests (local development)
test: test-rust test-integration
	@echo "✅ All tests passed!"

# Run Rust unit + snapshot tests
test-rust:
	cd warp_core && cargo test --lib --bins --tests

# Run basic integration test
test-integration:
	./tooling/test_runner.sh integration

# Run specific integration tests
test-integration-malformed:
	./tooling/test_runner.sh malformed

test-integration-partialutf8:
	./tooling/test_runner.sh partialutf8

test-integration-longscroll:
	./tooling/test_runner.sh longscroll

test-integration-overlapping:
	./tooling/test_runner.sh overlapping

test-integration-cjk:
	./tooling/test_runner.sh cjk

test-integration-partialescape:
	./tooling/test_runner.sh partialescape

# Run all integration tests
test-integration-all:
	./tooling/test_runner.sh all

# Run UI tests (requires dev server at localhost:4000)
test-ui:
	cd ui-tests && npm ci && npm run test:ui

# Generate long scroll fixture
generate-longscroll:
	python3 tooling/generate_long_scroll.py 50000

# Build all components
build-all:
	@echo "Building Rust core..."
	cd warp_core && cargo build --release
	@echo "Building web UI (if exists)..."
	@if [ -d app/gui-electron ]; then \
		cd app/gui-electron && npm ci && npm run build || true; \
	fi

# CI target (build + test)
ci: build-all test
	@echo "✅ CI checks passed!"
