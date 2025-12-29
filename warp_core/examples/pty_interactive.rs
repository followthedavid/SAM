// Test PTY input/output
use std::io::{self, BufRead};
use std::sync::mpsc;
use std::thread;
use std::time::Duration;
use warp_core::pty::WarpPty;

fn main() {
    let (tx, rx) = mpsc::channel();
    
    println!("Spawning PTY...");
    let pty = WarpPty::spawn("/bin/zsh", tx).expect("Failed to spawn PTY");
    
    // Read thread - print output
    let read_thread = thread::spawn(move || {
        loop {
            match rx.recv_timeout(Duration::from_millis(100)) {
                Ok(data) => {
                    print!("{}", String::from_utf8_lossy(&data));
                    io::Write::flush(&mut io::stdout()).unwrap();
                }
                Err(_) => {}
            }
        }
    });
    
    // Wait a bit for initial prompt
    thread::sleep(Duration::from_millis(500));
    
    println!("\n\n=== Testing input: 'echo hello' ===");
    pty.write_input(b"echo hello\n").unwrap();
    
    thread::sleep(Duration::from_millis(500));
    
    println!("\n=== Testing input: 'pwd' ===");
    pty.write_input(b"pwd\n").unwrap();
    
    thread::sleep(Duration::from_millis(500));
    
    println!("\n=== Testing polling-based read ===");
    let output = pty.read_output().unwrap();
    println!("Buffered output: {:?}", String::from_utf8_lossy(&output));
    
    println!("\n=== Test complete ===");
    
    // Clean exit
    pty.write_input(b"exit\n").unwrap();
    thread::sleep(Duration::from_millis(200));
}
