# warp_core Quick Start

## 🚀 5-Minute Integration Guide

### Prerequisites
- Rust installed ✅ (already done)
- Cargo available ✅ (already done)
- warp_core built ✅ (already done)

### Option 1: Test Rust Crate Directly (Fastest)

```bash
cd /Users/davidquinton/ReverseLab/Warp_Open/warp_core

# Run all tests
cargo test

# Try it in a Rust script
cargo new --bin test_warp_core
cd test_warp_core
```

Add to `Cargo.toml`:
```toml
[dependencies]
warp_core = { path = "../" }
tokio = { version = "1", features = ["full"] }
```

Add to `src/main.rs`:
```rust
use warp_core::*;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Test file operations
    let test_file = "/tmp/warp_test.txt";
    write_text_file(test_file, "Hello from Rust!", WriteFileOpts::default()).await?;
    let content = read_text_file(test_file, ReadFileOpts::default()).await?;
    println!("Read: {}", content);

    // Test journal
    let journal = Journal::new();
    journal.log_action("test", "My first action", None).await?;
    let entries = journal.get_entries(0, 5).await?;
    println!("Journal entries: {}", entries.len());

    Ok(())
}
```

Run it:
```bash
cargo run
```

### Option 2: Bridge to Node.js with napi-rs

#### Step 1: Install napi-rs CLI
```bash
npm install -g @napi-rs/cli
```

#### Step 2: Add napi dependencies
```bash
cd /Users/davidquinton/ReverseLab/Warp_Open/warp_core

# Edit Cargo.toml and add:
# [dependencies]
# napi = "2"
# napi-derive = "2"
# 
# [lib]
# crate-type = ["cdylib"]

cargo add napi napi-derive
```

#### Step 3: Update Cargo.toml lib section
```bash
cat >> Cargo.toml << 'EOF'

[lib]
crate-type = ["cdylib"]

[features]
napi = ["dep:napi", "dep:napi-derive"]
EOF
```

#### Step 4: Copy napi bridge example to lib
```bash
# The napi_bridge.rs example shows how to expose functions
# You can either integrate it into src/lib.rs or create a separate crate
```

#### Step 5: Build native module
```bash
napi build --platform --release
```

#### Step 6: Test from Node.js
```javascript
// test.js
const warpCore = require('./warp_core.node');

(async () => {
  const id = warpCore.generateId('test');
  console.log('Generated ID:', id);

  await warpCore.logAction('test', 'Node.js integration test', null);
  const entries = JSON.parse(await warpCore.getJournalEntries(0, 5));
  console.log('Journal entries:', entries.length);
})();
```

```bash
node test.js
```

### Option 3: Quick Tauri Test

```bash
cd /Users/davidquinton/ReverseLab/Warp_Open

# Install Tauri CLI if needed
cargo install tauri-cli --version "^2"

# Initialize Tauri (will not overwrite existing files)
cargo tauri init

# Add warp_core to src-tauri/Cargo.toml
cd src-tauri
cargo add --path ../warp_core
```

Add Tauri command to `src-tauri/src/main.rs`:
```rust
use warp_core::*;

#[tauri::command]
async fn read_file_rust(path: String) -> Result<String, String> {
    let opts = ReadFileOpts::default();
    read_text_file(path, opts)
        .await
        .map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![read_file_rust])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## 📊 Performance Test

Create `benchmark.rs`:
```rust
use warp_core::*;
use std::time::Instant;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let iterations = 1000;
    let start = Instant::now();
    
    for i in 0..iterations {
        let _ = make_id(&format!("bench-{}", i));
    }
    
    let duration = start.elapsed();
    println!("Generated {} IDs in {:?}", iterations, duration);
    println!("Avg: {:?} per ID", duration / iterations);

    // Test journal performance
    let journal = Journal::new();
    let start = Instant::now();
    
    for i in 0..100 {
        journal.log_action("perf", format!("Action {}", i), None).await?;
    }
    
    let duration = start.elapsed();
    println!("Logged 100 actions in {:?}", duration);
    println!("Avg: {:?} per action", duration / 100);

    Ok(())
}
```

## 🔍 Verify Installation

```bash
cd /Users/davidquinton/ReverseLab/Warp_Open/warp_core

# Check all tests pass
cargo test

# Check documentation builds
cargo doc --no-deps --open

# Check release build works
cargo build --release

# Check clippy (linter) is happy
cargo clippy
```

## 📝 Next Steps

1. **Choose Integration Path** (see PHASE5_SUMMARY.md)
   - napi-rs for Node.js integration
   - Tauri for full Rust migration
   - HTTP service for flexibility

2. **Read Documentation**
   - README.md - Architecture and API reference
   - PHASE5_SUMMARY.md - Complete overview
   - `cargo doc --open` - Rust API docs

3. **Experiment**
   - Modify examples
   - Add new features
   - Profile performance

## 🐛 Troubleshooting

### Cargo not found
```bash
source "$HOME/.cargo/env"
```

### Tests fail
```bash
# Clear journal from previous tests
rm ~/.warp_open/warp_history.json
cargo test
```

### Build errors
```bash
# Update dependencies
cargo update
cargo build
```

### napi-rs issues
```bash
# Ensure Node.js is installed
node --version
npm --version

# Reinstall napi-rs CLI
npm install -g @napi-rs/cli --force
```

## 💡 Pro Tips

1. **Use `cargo watch`** for auto-rebuild during development:
   ```bash
   cargo install cargo-watch
   cargo watch -x test
   ```

2. **Profile performance** with `cargo flamegraph`:
   ```bash
   cargo install flamegraph
   cargo flamegraph --bin your_binary
   ```

3. **Check code coverage** with `cargo tarpaulin`:
   ```bash
   cargo install cargo-tarpaulin
   cargo tarpaulin --out Html
   ```

4. **Format code** with `cargo fmt`:
   ```bash
   cargo fmt
   ```

5. **Security audit**:
   ```bash
   cargo install cargo-audit
   cargo audit
   ```

## 📚 Resources

- [Rust Book](https://doc.rust-lang.org/book/)
- [Tokio Docs](https://tokio.rs/)
- [napi-rs Guide](https://napi.rs/)
- [Tauri Docs](https://tauri.app/)
- [Anyhow Error Handling](https://docs.rs/anyhow/)

## ✅ Success Criteria

You've successfully integrated warp_core when:

- [ ] All tests pass: `cargo test`
- [ ] Can call Rust functions from your app
- [ ] Journal persists to `~/.warp_open/warp_history.json`
- [ ] File operations work as expected
- [ ] Performance meets or exceeds Node.js version

Ready to go! 🚀
