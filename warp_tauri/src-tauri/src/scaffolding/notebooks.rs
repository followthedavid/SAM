//! Interactive Notebooks - Warp-style command notebooks
//!
//! Provides notebook functionality:
//! - Code cells (executable commands)
//! - Markdown cells (documentation)
//! - Output capture and display
//! - Cell execution state
//! - Notebook persistence

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

// =============================================================================
// TYPES
// =============================================================================

/// Cell type in a notebook
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CellType {
    /// Executable command cell
    Code,
    /// Markdown documentation cell
    Markdown,
    /// Raw text cell
    Raw,
}

/// Cell execution state
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub enum CellState {
    #[default]
    Idle,
    Running,
    Success,
    Error,
    Cancelled,
}

/// Cell output
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CellOutput {
    /// Output type (stdout, stderr, result, error)
    pub output_type: OutputType,
    /// Output content
    pub content: String,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum OutputType {
    Stdout,
    Stderr,
    Result,
    Error,
    Image,
    Html,
}

/// A notebook cell
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Cell {
    /// Unique cell ID
    pub id: String,
    /// Cell type
    pub cell_type: CellType,
    /// Cell content (command or markdown)
    pub source: String,
    /// Execution state
    pub state: CellState,
    /// Outputs (for code cells)
    pub outputs: Vec<CellOutput>,
    /// Execution count (increments each run)
    pub execution_count: Option<u32>,
    /// Metadata
    pub metadata: CellMetadata,
    /// Created timestamp
    pub created_at: DateTime<Utc>,
    /// Last modified
    pub modified_at: DateTime<Utc>,
    /// Last executed
    pub executed_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CellMetadata {
    /// Cell is collapsed
    pub collapsed: bool,
    /// Cell is scrolled (for long output)
    pub scrolled: bool,
    /// Custom tags
    pub tags: Vec<String>,
    /// Execution timeout in seconds
    pub timeout: Option<u32>,
    /// Working directory override
    pub cwd: Option<String>,
    /// Environment variables
    pub env: HashMap<String, String>,
}

/// A notebook
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Notebook {
    /// Unique notebook ID
    pub id: String,
    /// Notebook title
    pub title: String,
    /// Description
    pub description: Option<String>,
    /// Cells in order
    pub cells: Vec<Cell>,
    /// Notebook metadata
    pub metadata: NotebookMetadata,
    /// Created timestamp
    pub created_at: DateTime<Utc>,
    /// Last modified
    pub modified_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct NotebookMetadata {
    /// Author
    pub author: Option<String>,
    /// Tags for organization
    pub tags: Vec<String>,
    /// Default shell
    pub shell: Option<String>,
    /// Default working directory
    pub cwd: Option<String>,
    /// Environment variables
    pub env: HashMap<String, String>,
    /// Is favorite/starred
    pub starred: bool,
    /// Version
    pub version: u32,
}

// =============================================================================
// NOTEBOOK MANAGER
// =============================================================================

pub struct NotebookManager {
    notebooks: HashMap<String, Notebook>,
    active_notebook: Option<String>,
    execution_count: u32,
    event_handlers: Vec<Box<dyn Fn(&NotebookEvent) + Send + Sync>>,
}

#[derive(Debug, Clone)]
pub enum NotebookEvent {
    Created(String),
    Opened(String),
    Saved(String),
    CellAdded { notebook_id: String, cell_id: String },
    CellRemoved { notebook_id: String, cell_id: String },
    CellExecutionStarted { notebook_id: String, cell_id: String },
    CellExecutionCompleted { notebook_id: String, cell_id: String, success: bool },
    CellOutputAdded { notebook_id: String, cell_id: String },
}

impl NotebookManager {
    pub fn new() -> Self {
        Self {
            notebooks: HashMap::new(),
            active_notebook: None,
            execution_count: 0,
            event_handlers: Vec::new(),
        }
    }

    /// Create a new notebook
    pub fn create(&mut self, title: &str) -> &Notebook {
        let id = format!("nb_{}", chrono::Utc::now().timestamp_millis());
        let notebook = Notebook {
            id: id.clone(),
            title: title.to_string(),
            description: None,
            cells: Vec::new(),
            metadata: NotebookMetadata::default(),
            created_at: Utc::now(),
            modified_at: Utc::now(),
        };

        self.notebooks.insert(id.clone(), notebook);
        self.active_notebook = Some(id.clone());
        self.emit_event(NotebookEvent::Created(id.clone()));

        self.notebooks.get(&id).unwrap()
    }

    /// Open a notebook
    pub fn open(&mut self, id: &str) -> Option<&Notebook> {
        if self.notebooks.contains_key(id) {
            self.active_notebook = Some(id.to_string());
            self.emit_event(NotebookEvent::Opened(id.to_string()));
            self.notebooks.get(id)
        } else {
            None
        }
    }

    /// Get active notebook
    pub fn active(&self) -> Option<&Notebook> {
        self.active_notebook.as_ref().and_then(|id| self.notebooks.get(id))
    }

    /// Get active notebook mutably
    pub fn active_mut(&mut self) -> Option<&mut Notebook> {
        let id = self.active_notebook.clone()?;
        self.notebooks.get_mut(&id)
    }

    /// Add a code cell
    pub fn add_code_cell(&mut self, source: &str) -> Option<String> {
        let notebook_id = self.active_notebook.clone()?;
        let cell = self.create_cell(CellType::Code, source);
        let cell_id = cell.id.clone();

        if let Some(notebook) = self.notebooks.get_mut(&notebook_id) {
            notebook.cells.push(cell);
            notebook.modified_at = Utc::now();
            self.emit_event(NotebookEvent::CellAdded {
                notebook_id,
                cell_id: cell_id.clone(),
            });
            Some(cell_id)
        } else {
            None
        }
    }

    /// Add a markdown cell
    pub fn add_markdown_cell(&mut self, source: &str) -> Option<String> {
        let notebook_id = self.active_notebook.clone()?;
        let cell = self.create_cell(CellType::Markdown, source);
        let cell_id = cell.id.clone();

        if let Some(notebook) = self.notebooks.get_mut(&notebook_id) {
            notebook.cells.push(cell);
            notebook.modified_at = Utc::now();
            self.emit_event(NotebookEvent::CellAdded {
                notebook_id,
                cell_id: cell_id.clone(),
            });
            Some(cell_id)
        } else {
            None
        }
    }

    /// Insert cell at position
    pub fn insert_cell(&mut self, index: usize, cell_type: CellType, source: &str) -> Option<String> {
        let notebook_id = self.active_notebook.clone()?;
        let cell = self.create_cell(cell_type, source);
        let cell_id = cell.id.clone();

        if let Some(notebook) = self.notebooks.get_mut(&notebook_id) {
            let idx = index.min(notebook.cells.len());
            notebook.cells.insert(idx, cell);
            notebook.modified_at = Utc::now();
            self.emit_event(NotebookEvent::CellAdded {
                notebook_id,
                cell_id: cell_id.clone(),
            });
            Some(cell_id)
        } else {
            None
        }
    }

    /// Remove a cell
    pub fn remove_cell(&mut self, cell_id: &str) -> bool {
        let notebook_id = match &self.active_notebook {
            Some(id) => id.clone(),
            None => return false,
        };

        if let Some(notebook) = self.notebooks.get_mut(&notebook_id) {
            let original_len = notebook.cells.len();
            notebook.cells.retain(|c| c.id != cell_id);
            if notebook.cells.len() < original_len {
                notebook.modified_at = Utc::now();
                self.emit_event(NotebookEvent::CellRemoved {
                    notebook_id,
                    cell_id: cell_id.to_string(),
                });
                return true;
            }
        }
        false
    }

    /// Move cell up
    pub fn move_cell_up(&mut self, cell_id: &str) -> bool {
        if let Some(notebook) = self.active_mut() {
            if let Some(idx) = notebook.cells.iter().position(|c| c.id == cell_id) {
                if idx > 0 {
                    notebook.cells.swap(idx, idx - 1);
                    notebook.modified_at = Utc::now();
                    return true;
                }
            }
        }
        false
    }

    /// Move cell down
    pub fn move_cell_down(&mut self, cell_id: &str) -> bool {
        if let Some(notebook) = self.active_mut() {
            if let Some(idx) = notebook.cells.iter().position(|c| c.id == cell_id) {
                if idx < notebook.cells.len() - 1 {
                    notebook.cells.swap(idx, idx + 1);
                    notebook.modified_at = Utc::now();
                    return true;
                }
            }
        }
        false
    }

    /// Update cell source
    pub fn update_cell(&mut self, cell_id: &str, source: &str) -> bool {
        if let Some(notebook) = self.active_mut() {
            if let Some(cell) = notebook.cells.iter_mut().find(|c| c.id == cell_id) {
                cell.source = source.to_string();
                cell.modified_at = Utc::now();
                notebook.modified_at = Utc::now();
                return true;
            }
        }
        false
    }

    /// Execute a cell (simulated - returns the command to run)
    pub fn execute_cell(&mut self, cell_id: &str) -> Option<ExecutionRequest> {
        let notebook_id = self.active_notebook.clone()?;

        // First update the cell and collect the info we need
        self.execution_count += 1;
        let exec_count = self.execution_count;

        let request = {
            let notebook = self.notebooks.get_mut(&notebook_id)?;
            let cell = notebook.cells.iter_mut().find(|c| c.id == cell_id)?;

            if cell.cell_type != CellType::Code {
                return None;
            }

            cell.execution_count = Some(exec_count);
            cell.state = CellState::Running;
            cell.outputs.clear();
            cell.executed_at = Some(Utc::now());

            let request = ExecutionRequest {
                notebook_id: notebook_id.clone(),
                cell_id: cell_id.to_string(),
                command: cell.source.clone(),
                cwd: cell.metadata.cwd.clone().or_else(|| notebook.metadata.cwd.clone()),
                env: {
                    let mut env = notebook.metadata.env.clone();
                    env.extend(cell.metadata.env.clone());
                    env
                },
                timeout: cell.metadata.timeout,
            };
            request
        };

        // Emit event outside the mutable borrow
        self.emit_event(NotebookEvent::CellExecutionStarted {
            notebook_id,
            cell_id: cell_id.to_string(),
        });

        Some(request)
    }

    /// Record cell output
    pub fn add_output(&mut self, cell_id: &str, output_type: OutputType, content: &str) {
        let notebook_id = match &self.active_notebook {
            Some(id) => id.clone(),
            None => return,
        };

        if let Some(notebook) = self.notebooks.get_mut(&notebook_id) {
            if let Some(cell) = notebook.cells.iter_mut().find(|c| c.id == cell_id) {
                cell.outputs.push(CellOutput {
                    output_type,
                    content: content.to_string(),
                    timestamp: Utc::now(),
                });
                self.emit_event(NotebookEvent::CellOutputAdded {
                    notebook_id,
                    cell_id: cell_id.to_string(),
                });
            }
        }
    }

    /// Complete cell execution
    pub fn complete_execution(&mut self, cell_id: &str, success: bool) {
        let notebook_id = match &self.active_notebook {
            Some(id) => id.clone(),
            None => return,
        };

        if let Some(notebook) = self.notebooks.get_mut(&notebook_id) {
            if let Some(cell) = notebook.cells.iter_mut().find(|c| c.id == cell_id) {
                cell.state = if success { CellState::Success } else { CellState::Error };
                self.emit_event(NotebookEvent::CellExecutionCompleted {
                    notebook_id,
                    cell_id: cell_id.to_string(),
                    success,
                });
            }
        }
    }

    /// Execute all cells in order
    pub fn execute_all(&mut self) -> Vec<ExecutionRequest> {
        let notebook_id = match &self.active_notebook {
            Some(id) => id.clone(),
            None => return Vec::new(),
        };

        let cell_ids: Vec<String> = self.notebooks
            .get(&notebook_id)
            .map(|nb| nb.cells.iter()
                .filter(|c| c.cell_type == CellType::Code)
                .map(|c| c.id.clone())
                .collect())
            .unwrap_or_default();

        cell_ids.iter()
            .filter_map(|id| self.execute_cell(id))
            .collect()
    }

    /// Clear all outputs
    pub fn clear_outputs(&mut self) {
        if let Some(notebook) = self.active_mut() {
            for cell in &mut notebook.cells {
                cell.outputs.clear();
                cell.state = CellState::Idle;
            }
            notebook.modified_at = Utc::now();
        }
    }

    /// Get notebook by ID
    pub fn get(&self, id: &str) -> Option<&Notebook> {
        self.notebooks.get(id)
    }

    /// List all notebooks
    pub fn list(&self) -> Vec<&Notebook> {
        self.notebooks.values().collect()
    }

    /// Delete a notebook
    pub fn delete(&mut self, id: &str) -> bool {
        if self.notebooks.remove(id).is_some() {
            if self.active_notebook.as_deref() == Some(id) {
                self.active_notebook = None;
            }
            true
        } else {
            false
        }
    }

    /// Export notebook to JSON
    pub fn export_json(&self, id: &str) -> Option<String> {
        self.notebooks.get(id).and_then(|nb| serde_json::to_string_pretty(nb).ok())
    }

    /// Import notebook from JSON
    pub fn import_json(&mut self, json: &str) -> Option<String> {
        let notebook: Notebook = serde_json::from_str(json).ok()?;
        let id = notebook.id.clone();
        self.notebooks.insert(id.clone(), notebook);
        Some(id)
    }

    /// Export notebook to markdown
    pub fn export_markdown(&self, id: &str) -> Option<String> {
        let notebook = self.notebooks.get(id)?;
        let mut md = format!("# {}\n\n", notebook.title);

        if let Some(ref desc) = notebook.description {
            md.push_str(&format!("{}\n\n", desc));
        }

        for cell in &notebook.cells {
            match cell.cell_type {
                CellType::Code => {
                    md.push_str(&format!("```bash\n{}\n```\n\n", cell.source));
                    for output in &cell.outputs {
                        if output.output_type == OutputType::Stdout {
                            md.push_str(&format!("Output:\n```\n{}\n```\n\n", output.content));
                        }
                    }
                }
                CellType::Markdown => {
                    md.push_str(&format!("{}\n\n", cell.source));
                }
                CellType::Raw => {
                    md.push_str(&format!("```\n{}\n```\n\n", cell.source));
                }
            }
        }

        Some(md)
    }

    fn create_cell(&self, cell_type: CellType, source: &str) -> Cell {
        Cell {
            id: format!("cell_{}", chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0)),
            cell_type,
            source: source.to_string(),
            state: CellState::Idle,
            outputs: Vec::new(),
            execution_count: None,
            metadata: CellMetadata::default(),
            created_at: Utc::now(),
            modified_at: Utc::now(),
            executed_at: None,
        }
    }

    /// Register event handler
    pub fn on_event<F>(&mut self, handler: F)
    where
        F: Fn(&NotebookEvent) + Send + Sync + 'static,
    {
        self.event_handlers.push(Box::new(handler));
    }

    fn emit_event(&self, event: NotebookEvent) {
        for handler in &self.event_handlers {
            handler(&event);
        }
    }
}

impl Default for NotebookManager {
    fn default() -> Self {
        Self::new()
    }
}

/// Request to execute a cell
#[derive(Debug, Clone)]
pub struct ExecutionRequest {
    pub notebook_id: String,
    pub cell_id: String,
    pub command: String,
    pub cwd: Option<String>,
    pub env: HashMap<String, String>,
    pub timeout: Option<u32>,
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref NOTEBOOK_MANAGER: Arc<Mutex<NotebookManager>> =
        Arc::new(Mutex::new(NotebookManager::new()));
}

/// Get the global notebook manager
pub fn notebooks() -> Arc<Mutex<NotebookManager>> {
    NOTEBOOK_MANAGER.clone()
}

/// Create a new notebook
pub fn create(title: &str) -> String {
    NOTEBOOK_MANAGER.lock().unwrap().create(title).id.clone()
}

/// Add a code cell to the active notebook
pub fn add_code(source: &str) -> Option<String> {
    NOTEBOOK_MANAGER.lock().unwrap().add_code_cell(source)
}

/// Add a markdown cell to the active notebook
pub fn add_markdown(source: &str) -> Option<String> {
    NOTEBOOK_MANAGER.lock().unwrap().add_markdown_cell(source)
}

/// Execute a cell
pub fn execute(cell_id: &str) -> Option<ExecutionRequest> {
    NOTEBOOK_MANAGER.lock().unwrap().execute_cell(cell_id)
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_notebook() {
        let mut manager = NotebookManager::new();
        let notebook = manager.create("Test Notebook");
        assert_eq!(notebook.title, "Test Notebook");
        assert!(notebook.cells.is_empty());
    }

    #[test]
    fn test_add_cells() {
        let mut manager = NotebookManager::new();
        manager.create("Test");

        let code_id = manager.add_code_cell("ls -la").unwrap();
        let md_id = manager.add_markdown_cell("# Header").unwrap();

        let notebook = manager.active().unwrap();
        assert_eq!(notebook.cells.len(), 2);
        assert_eq!(notebook.cells[0].id, code_id);
        assert_eq!(notebook.cells[1].id, md_id);
    }

    #[test]
    fn test_execute_cell() {
        let mut manager = NotebookManager::new();
        manager.create("Test");
        let cell_id = manager.add_code_cell("echo hello").unwrap();

        let request = manager.execute_cell(&cell_id).unwrap();
        assert_eq!(request.command, "echo hello");

        let notebook = manager.active().unwrap();
        let cell = notebook.cells.iter().find(|c| c.id == cell_id).unwrap();
        assert_eq!(cell.state, CellState::Running);
    }

    #[test]
    fn test_move_cells() {
        let mut manager = NotebookManager::new();
        manager.create("Test");
        let id1 = manager.add_code_cell("cmd1").unwrap();
        let id2 = manager.add_code_cell("cmd2").unwrap();

        assert!(manager.move_cell_down(&id1));

        let notebook = manager.active().unwrap();
        assert_eq!(notebook.cells[0].id, id2);
        assert_eq!(notebook.cells[1].id, id1);
    }

    #[test]
    fn test_export_markdown() {
        let mut manager = NotebookManager::new();
        manager.create("Export Test");
        manager.add_markdown_cell("# Documentation");
        manager.add_code_cell("echo hello");

        let notebook_id = manager.active().unwrap().id.clone();
        let md = manager.export_markdown(&notebook_id).unwrap();

        assert!(md.contains("# Export Test"));
        assert!(md.contains("# Documentation"));
        assert!(md.contains("```bash"));
        assert!(md.contains("echo hello"));
    }

    #[test]
    fn test_clear_outputs() {
        let mut manager = NotebookManager::new();
        manager.create("Test");
        let cell_id = manager.add_code_cell("test").unwrap();

        manager.add_output(&cell_id, OutputType::Stdout, "output");

        {
            let notebook = manager.active().unwrap();
            assert!(!notebook.cells[0].outputs.is_empty());
        }

        manager.clear_outputs();

        let notebook = manager.active().unwrap();
        assert!(notebook.cells[0].outputs.is_empty());
    }

    #[test]
    fn test_import_export_json() {
        let mut manager = NotebookManager::new();
        manager.create("JSON Test");
        manager.add_code_cell("test command");

        let notebook_id = manager.active().unwrap().id.clone();
        let json = manager.export_json(&notebook_id).unwrap();

        let imported_id = manager.import_json(&json).unwrap();
        let imported = manager.get(&imported_id).unwrap();

        assert_eq!(imported.title, "JSON Test");
        assert_eq!(imported.cells.len(), 1);
    }
}
