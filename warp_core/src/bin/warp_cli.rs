/*!
 * Warp Core CLI - PTY Stream Parser
 * 
 * Real-time command-line tool for parsing PTY streams with OSC 133 sequences.
 * Emits structured JSON events for integration with automation pipelines.
 */

use std::io::{self, BufRead, Write, Read};
use std::path::PathBuf;
use std::fs::File;
use std::sync::mpsc;
use std::thread;
use clap::{Parser, Subcommand};
use warp_core::osc_parser::{OSC133Parser, OSC133Type};
use warp_core::pty::WarpPty;

#[derive(Parser)]
#[command(name = "warp_cli")]
#[command(about = "Warp Core - PTY Stream Parser and Automation Tool", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Parse PTY stream with OSC 133 markers
    ParseStream {
        /// Input file (stdin if not provided)
        #[arg(short, long)]
        input: Option<PathBuf>,
        
        /// Output file (stdout if not provided)
        #[arg(short, long)]
        output: Option<PathBuf>,
        
        /// Emit JSON events instead of human-readable format
        #[arg(short, long)]
        json: bool,
        
        /// Use heuristic fallback for streams without OSC markers
        #[arg(short = 'H', long)]
        heuristic: bool,
    },
    
    /// Run an interactive PTY session
    RunPty {
        /// Shell to spawn (default: $SHELL or /bin/sh)
        #[arg(short, long)]
        shell: Option<String>,
    },
    
    /// Show version information
    Version,
}

fn main() {
    let cli = Cli::parse();
    
    match cli.command {
        Commands::ParseStream { input, output, json, heuristic } => {
            if let Err(e) = parse_stream(input, output, json, heuristic) {
                eprintln!("Error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::RunPty { shell } => {
            let shell_path = shell.or_else(|| std::env::var("SHELL").ok())
                .unwrap_or_else(|| "/bin/sh".to_string());
            
            if let Err(e) = run_pty(&shell_path) {
                eprintln!("PTY Error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::Version => {
            println!("warp_cli v{}", env!("CARGO_PKG_VERSION"));
            println!("Warp Core PTY Parser and Automation Tool");
        }
    }
}

fn run_pty(shell: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Create channel for PTY output
    let (output_tx, output_rx) = mpsc::channel();
    
    // Spawn PTY with the specified shell
    let pty = WarpPty::spawn(shell, output_tx)?;
    
    // Create channel for stdin → PTY
    let (stdin_tx, stdin_rx) = mpsc::channel::<Vec<u8>>();
    
    // Spawn thread to read stdin
    let stdin_thread = thread::spawn(move || {
        let stdin = io::stdin();
        let mut buf = [0u8; 1024];
        loop {
            match stdin.lock().read(&mut buf) {
                Ok(0) => break, // EOF
                Ok(n) => {
                    if stdin_tx.send(buf[..n].to_vec()).is_err() {
                        break; // PTY closed
                    }
                }
                Err(_) => break,
            }
        }
    });
    
    // Spawn thread to forward stdin data to PTY
    let pty_writer_thread = thread::spawn(move || {
        while let Ok(data) = stdin_rx.recv() {
            if pty.write_input(&data).is_err() {
                break;
            }
        }
    });
    
    // Main thread: print PTY output to stdout
    let stdout = io::stdout();
    let mut stdout_lock = stdout.lock();
    
    while let Ok(data) = output_rx.recv() {
        stdout_lock.write_all(&data)?;
        stdout_lock.flush()?;
    }
    
    // Wait for threads to finish
    let _ = stdin_thread.join();
    let _ = pty_writer_thread.join();
    
    Ok(())
}

fn parse_stream(
    input: Option<PathBuf>,
    output: Option<PathBuf>,
    json: bool,
    use_heuristic: bool,
) -> io::Result<()> {
    // Open input (stdin or file)
    let stdin = io::stdin();
    let input_reader: Box<dyn BufRead> = if let Some(path) = input {
        Box::new(io::BufReader::new(File::open(path)?))
    } else {
        Box::new(stdin.lock())
    };
    
    // Open output (stdout or file)
    let stdout = io::stdout();
    let mut output_writer: Box<dyn Write> = if let Some(path) = output {
        Box::new(File::create(path)?)
    } else {
        Box::new(stdout.lock())
    };
    
    let mut parser = OSC133Parser::new();
    let mut block_count = 0;
    let mut current_block = BlockBuilder::new();
    
    // Process input line by line
    for line in input_reader.lines() {
        let line = line?;
        
        // Try to parse OSC 133 sequences
        if let Some(event) = parser.feed_line(&line) {
            match event {
                OSC133Type::PromptStart => {
                    // Start new block
                    if current_block.has_content() {
                        emit_block(&mut output_writer, &current_block, json, &mut block_count)?;
                        current_block = BlockBuilder::new();
                    }
                    current_block.set_type("input");
                }
                OSC133Type::CommandStart => {
                    current_block.set_type("input");
                }
                OSC133Type::CommandEnd => {
                    current_block.set_type("output");
                }
                OSC133Type::CommandFinished { exit_code } => {
                    if let Some(code) = exit_code {
                        if code != 0 {
                            current_block.set_type("error");
                        }
                        current_block.set_exit_code(code);
                    }
                }
                OSC133Type::Unknown(seq) => {
                    if json {
                        eprintln!("Unknown OSC sequence: {}", seq);
                    }
                }
            }
        }
        
        // Add line to current block
        current_block.add_line(&line);
        
        // Heuristic: detect block boundaries without OSC markers
        if use_heuristic && parser.get_last_event().is_none() {
            if is_prompt_line(&line) && current_block.has_content() {
                emit_block(&mut output_writer, &current_block, json, &mut block_count)?;
                current_block = BlockBuilder::new();
                current_block.set_type("input");
            }
        }
    }
    
    // Emit final block
    if current_block.has_content() {
        emit_block(&mut output_writer, &current_block, json, &mut block_count)?;
    }
    
    if !json {
        writeln!(output_writer, "\n✅ Parsed {} blocks", block_count)?;
    }
    
    Ok(())
}

fn emit_block(
    writer: &mut Box<dyn Write>,
    block: &BlockBuilder,
    json: bool,
    block_count: &mut usize,
) -> io::Result<()> {
    *block_count += 1;
    
    if json {
        // Emit JSON event
        let event = serde_json::json!({
            "type": "block",
            "id": *block_count,
            "block_type": block.block_type,
            "content": block.content,
            "exit_code": block.exit_code,
            "line_count": block.line_count,
        });
        writeln!(writer, "{}", event)?;
    } else {
        // Human-readable format
        writeln!(writer, "\n--- Block {} ({}) ---", block_count, block.block_type)?;
        writeln!(writer, "{}", block.content)?;
        if let Some(code) = block.exit_code {
            writeln!(writer, "Exit Code: {}", code)?;
        }
    }
    
    Ok(())
}

fn is_prompt_line(line: &str) -> bool {
    // Heuristic: line ends with $ or % or >
    let trimmed = line.trim();
    trimmed.ends_with('$') || trimmed.ends_with('%') || trimmed.ends_with('>')
}

struct BlockBuilder {
    block_type: String,
    content: String,
    exit_code: Option<i32>,
    line_count: usize,
}

impl BlockBuilder {
    fn new() -> Self {
        Self {
            block_type: "unknown".to_string(),
            content: String::new(),
            exit_code: None,
            line_count: 0,
        }
    }
    
    fn set_type(&mut self, block_type: &str) {
        self.block_type = block_type.to_string();
    }
    
    fn add_line(&mut self, line: &str) {
        if !self.content.is_empty() {
            self.content.push('\n');
        }
        self.content.push_str(line);
        self.line_count += 1;
    }
    
    fn set_exit_code(&mut self, code: i32) {
        self.exit_code = Some(code);
    }
    
    fn has_content(&self) -> bool {
        !self.content.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_prompt_detection() {
        assert!(is_prompt_line("user@host:~ $ "));
        assert!(is_prompt_line("user@host:~ % "));
        assert!(is_prompt_line("> "));
        assert!(!is_prompt_line("normal line"));
    }
    
    #[test]
    fn test_block_builder() {
        let mut builder = BlockBuilder::new();
        builder.set_type("input");
        builder.add_line("ls -la");
        builder.set_exit_code(0);
        
        assert_eq!(builder.block_type, "input");
        assert!(builder.has_content());
        assert_eq!(builder.exit_code, Some(0));
        assert_eq!(builder.line_count, 1);
    }
}
