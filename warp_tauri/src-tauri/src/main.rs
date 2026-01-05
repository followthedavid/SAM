#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;
mod session;
mod osc_handler;
mod test_bridge;
mod conversation;
mod ai_parser;
mod rollback;
mod telemetry;
mod policy_store;
mod agents;
mod plan_store;
mod monitoring;
mod scheduler;
mod phase1_6_tests;
mod ollama;
mod ssh_session;
mod scaffolding;

use commands::{
    spawn_pty, send_input, resize_pty, read_pty, close_pty, start_pty_output_stream,
    ai_query, ai_query_stream,
    execute_shell, read_file, write_file, list_directory_tree, list_directory, current_working_dir,
    send_test_message, send_user_message,
    get_conversation_state, test_phase2_workflow, test_phase3_workflow, create_batch,
    get_batches, approve_batch, run_batch, get_autonomy_settings, update_autonomy_settings,
    set_batch_dependency, rollback_batch, telemetry_insert_event, telemetry_query_recent,
    telemetry_export_csv, phase4_trigger_trainer, policy_list_rules, policy_propose_diff,
    policy_list_suggestions, policy_apply_suggestion, policy_rollback, policy_reject_suggestion,
    phase5_generate_suggestions, agent_register, agent_update, agent_set_status, agent_list,
    agent_unregister, phase6_create_plan, phase6_get_plan, phase6_get_pending_plans,
    phase6_update_plan_status, phase6_update_plan_index, phase6_delete_plan,
    get_monitoring_events, clear_monitoring_phase, clear_monitoring_all, start_scheduler,
    stop_scheduler, run_phase1_6_auto, PtyRegistry,
    // New features
    edit_file, web_fetch, get_shell_completions, get_ai_completion,
    init_project_context, load_project_context_cmd,
    ssh_connect_password, ssh_connect_key, ssh_send_input, ssh_read_output,
    ssh_resize, ssh_disconnect, ssh_list_sessions, SshState,
    // Glob and Grep for code navigation
    glob_files, grep_files,
    // Scaffolded agent commands
    start_agent_task, list_agent_models, check_ollama_status, execute_agent_tool,
    // Unified agent commands (24/7 guaranteed success)
    start_unified_task, resume_unified_task, list_unified_tasks, get_unified_task_status,
    // Intelligence engine (instant, no AI latency)
    intelligence_run, intelligence_parse,
    // Intelligence V2 (comprehensive coverage)
    intelligence_v2_run, intelligence_v2_parse,
    // Session state (memory without AI)
    get_session_state, get_history, get_last_command, add_alias, detect_project, get_error_suggestion,
    // Smart edit (Claude Code style)
    smart_edit, edit_line, insert_after_line, delete_lines, regex_replace, undo_edit, create_file_safe, append_to_file,
    // Debug
    debug_log,
    // Workflows (Warp-style saved command sequences)
    workflow_create, workflow_add_step, workflow_list, workflow_get, workflow_resolve, workflow_delete, workflow_builtins,
    // Multi-edit (atomic multi-file transactions)
    multi_edit_begin, multi_edit_add, multi_edit_commit, multi_edit_rollback, multi_edit_list,
    // Todo tracker (Claude Code style task tracking)
    todo_add, todo_add_many, todo_set_status, todo_list, todo_stats, todo_remove, todo_clear, todo_clear_completed,
    // Command palette (Cmd+K fuzzy search)
    palette_search, palette_search_files, palette_update_files, palette_record_usage, palette_recent,
    // Pane manager (split panes / tabs)
    pane_new_tab, pane_close_tab, pane_switch_tab, pane_list_tabs, pane_split, pane_close, pane_focus,
    pane_focus_next, pane_focus_prev, pane_active, pane_set_pty, pane_layout, pane_sizes,
    // AI Options (hybrid router, embeddings, templates, models)
    ai_route_request, ai_routing_stats,
    embedding_index_directory, embedding_search, embedding_search_name, embedding_stats, embedding_save, embedding_load,
    template_list, template_get, template_search, template_fill, template_generate_prompt,
    model_select, model_stats, model_list_available, model_mark_loaded, model_mark_unloaded, model_record_result, model_get_idle,
    // Orchestrator (central integration layer)
    orchestrate_request, orchestrate_stats,
    // Browser bridge (ChatGPT/Claude via Playwright)
    poll_bridge_response, get_bridge_tasks, queue_browser_task,
    // Background tasks
    background_tasks_list, background_tasks_running, background_task_get,
    background_task_cancel, background_tasks_summary, background_tasks_formatted,
    background_index_directory,
    // Streaming
    stream_create_session, stream_poll, stream_close_session,
    stream_read_file, stream_search,
    // Hooks system
    hooks_init, hooks_list, hooks_register, hooks_unregister, hooks_set_enabled, hooks_run,
    // Skills system
    skills_list, skills_search, skills_parse, skills_execute, skills_execute_raw,
    // MCP (Model Context Protocol)
    mcp_add_server, mcp_connect, mcp_list_tools, mcp_call_tool, mcp_load_config, mcp_list_servers,
    // Speed Cache
    cache_get_stats, cache_check, cache_clear_all, cache_hit_rate,
    // Web Search
    cmd_web_search, cmd_web_fetch,
    // Config Files
    cmd_load_project_config, cmd_get_instructions, cmd_get_rules,
    // Parallel Agents
    cmd_execute_parallel, cmd_create_parallel_task, cmd_cancel_parallel_agents, cmd_parallel_stats,
    // Autocomplete
    cmd_get_completions, cmd_add_completion_history, cmd_autocomplete_stats,
    // Hot Reload
    cmd_watch_directory, cmd_unwatch_directory, cmd_start_watcher, cmd_stop_watcher,
    cmd_reindex, cmd_indexer_stats, cmd_watcher_running,
    // Autonomy Controls
    cmd_set_autonomy_level, cmd_get_autonomy_level, cmd_requires_approval, cmd_approve_action,
    cmd_dispatch_mode_on, cmd_dispatch_mode_off, cmd_is_dispatch_mode, cmd_autonomy_config,
    // Subagents
    cmd_create_delegation_plan, cmd_execute_delegation_plan, cmd_get_delegation_plan,
    cmd_cancel_delegation_plan, cmd_subagent_stats,
    // Privacy & Task Execution
    execute_action,
    // Test Harness (headless batch testing)
    test_run_suite, test_run_smoke, test_run_single, test_status, test_get_cases, test_run_custom,
};
use session::{save_session, load_session};
use ollama::{query_ollama_stream, query_ollama, query_ollama_chat, list_ollama_models};

// App version info command
#[tauri::command]
fn get_app_version() -> serde_json::Value {
    serde_json::json!({
        "version": env!("CARGO_PKG_VERSION"),
        "name": "Warp_Open",
        "build": if cfg!(debug_assertions) { "debug" } else { "release" },
        "target": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
    })
}
use tauri::{Manager, Menu, MenuItem, Submenu};
use test_bridge::TestBridge;
use conversation::ConversationState;
use telemetry::TelemetryStore;
use policy_store::PolicyStore;
use agents::AgentCoordinator;
use plan_store::PlanStore;
use monitoring::MonitoringState;
use scheduler::Scheduler;
use std::sync::{Arc, Mutex};
use std::panic;
use std::io::Write;
use std::fs::{File, OpenOptions};
use std::process;

// Custom panic hook for crash reporting
fn setup_panic_handler() {
    let default_hook = panic::take_hook();
    panic::set_hook(Box::new(move |panic_info| {
        // Get panic location and message
        let location = panic_info.location().map(|l| {
            format!("{}:{}:{}", l.file(), l.line(), l.column())
        }).unwrap_or_else(|| "unknown".to_string());

        let message = if let Some(s) = panic_info.payload().downcast_ref::<&str>() {
            s.to_string()
        } else if let Some(s) = panic_info.payload().downcast_ref::<String>() {
            s.clone()
        } else {
            "Unknown panic".to_string()
        };

        // Write crash log to file
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let crash_log_path = format!("{}/.warp_open/crash.log", home);

        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&crash_log_path)
        {
            let timestamp = chrono::Utc::now().to_rfc3339();
            let crash_report = format!(
                "\n=== CRASH REPORT ===\n\
                Timestamp: {}\n\
                Location: {}\n\
                Message: {}\n\
                Version: {}\n\
                OS: {} ({})\n\
                ====================\n",
                timestamp, location, message,
                env!("CARGO_PKG_VERSION"),
                std::env::consts::OS, std::env::consts::ARCH
            );
            let _ = file.write_all(crash_report.as_bytes());
            eprintln!("[CRASH] Panic logged to {}", crash_log_path);
        }

        // Call default handler (will print to stderr)
        default_hook(panic_info);
    }));
}

/// Single instance lock - prevents multiple app instances
fn acquire_single_instance_lock() -> Option<File> {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let lock_path = format!("{}/.warp_open/warp_open.lock", home);

    // Ensure directory exists
    let _ = std::fs::create_dir_all(format!("{}/.warp_open", home));

    // Try to create/open the lock file with exclusive access
    match OpenOptions::new()
        .write(true)
        .create(true)
        .open(&lock_path)
    {
        Ok(file) => {
            // Try to get exclusive lock using flock
            #[cfg(unix)]
            {
                use std::os::unix::io::AsRawFd;
                let fd = file.as_raw_fd();
                let result = unsafe { libc::flock(fd, libc::LOCK_EX | libc::LOCK_NB) };
                if result != 0 {
                    eprintln!("[SINGLE_INSTANCE] Another instance is already running. Focusing existing window...");
                    return None;
                }
            }

            // Write PID to lock file
            let mut f = file;
            let _ = f.write_all(format!("{}", process::id()).as_bytes());
            Some(f)
        }
        Err(e) => {
            eprintln!("[SINGLE_INSTANCE] Failed to create lock file: {}", e);
            None
        }
    }
}

fn main() {
    // Check for single instance FIRST
    let _lock = match acquire_single_instance_lock() {
        Some(lock) => lock,
        None => {
            eprintln!("[SINGLE_INSTANCE] Warp_Open is already running. Exiting.");
            process::exit(0);
        }
    };

    // Setup crash reporting
    setup_panic_handler();
    // Create menu with DevTools option
    let menu = Menu::new()
        .add_submenu(Submenu::new(
            "View",
            Menu::new()
                .add_native_item(MenuItem::Copy)
                .add_native_item(MenuItem::Paste)
                .add_native_item(MenuItem::SelectAll)
                .add_native_item(MenuItem::Separator)
                .add_item(tauri::CustomMenuItem::new("devtools".to_string(), "Toggle DevTools").accelerator("CmdOrCtrl+Shift+I"))
        ));
    
    // Initialize stores
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let warp_dir = format!("{}/.warp_open", home);
    std::fs::create_dir_all(&warp_dir).expect("Failed to create .warp_open directory");
    
    let telemetry_path = format!("{}/telemetry.sqlite", warp_dir);
    let telemetry_store = TelemetryStore::open(std::path::PathBuf::from(telemetry_path))
        .expect("Failed to open telemetry database");
    
    let policy_path = format!("{}/policy.sqlite", warp_dir);
    let policy_store = PolicyStore::open(std::path::PathBuf::from(policy_path))
        .expect("Failed to open policy database");
    
    let agent_coordinator = AgentCoordinator::new();
    
    let plan_path = format!("{}/plans.sqlite", warp_dir);
    let plan_store = PlanStore::open(std::path::PathBuf::from(plan_path))
        .expect("Failed to open plans database");
    
    let monitoring_state = MonitoringState::new();
    
    let plan_store_arc = Arc::new(Mutex::new(plan_store));
    
    // Initialize scheduler (10 second interval)
    let scheduler = Scheduler::new(
        Arc::clone(&plan_store_arc),
        monitoring_state.clone(),
        10
    );
    
    tauri::Builder::default()
        .menu(menu)
        .on_menu_event(|event| {
            match event.menu_item_id() {
                "devtools" => {
                    #[cfg(debug_assertions)]
                    event.window().open_devtools();
                }
                _ => {}
            }
        })
        .manage(PtyRegistry::new())
        .manage(ConversationState::new())
        .manage(SshState::new())
        .manage(Arc::new(Mutex::new(telemetry_store)))
        .manage(Arc::new(Mutex::new(policy_store)))
        .manage(agent_coordinator)
        .manage(plan_store_arc)
        .manage(monitoring_state)
        .manage(scheduler)
        .setup(|app| {
            // Get the main window and set focus
            if let Some(window) = app.get_window("main") {
                let _ = window.set_focus();

                // Enable macOS vibrancy for glass effect
                #[cfg(target_os = "macos")]
                {
                    use window_vibrancy::{apply_vibrancy, NSVisualEffectMaterial, NSVisualEffectState};
                    // Use .Active state so it looks the same even when window isn't focused
                    let _ = apply_vibrancy(&window, NSVisualEffectMaterial::HudWindow, Some(NSVisualEffectState::Active), None);
                }
            }

            // Start test bridge if enabled
            let bridge = TestBridge::new();
            let app_handle = app.app_handle();
            tauri::async_runtime::spawn(async move {
                bridge.start(app_handle).await;
            });

            // Auto-index current directory for semantic search
            std::thread::spawn(|| {
                use crate::scaffolding::embeddings;

                let cwd = std::env::current_dir()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_else(|_| ".".to_string());

                eprintln!("[STARTUP] Auto-indexing {} for semantic search...", cwd);

                let extensions = &["rs", "ts", "tsx", "js", "jsx", "py", "go", "java", "cpp", "c", "h"];
                let mut engine = embeddings();

                match engine.index_directory(&cwd, extensions) {
                    Ok(stats) => {
                        eprintln!("[STARTUP] Indexed {} chunks from {} files",
                            stats.total_chunks, stats.total_files);
                    }
                    Err(e) => {
                        eprintln!("[STARTUP] Indexing failed (non-fatal): {}", e);
                    }
                }
            });

            // Pre-warm Ollama model to avoid 78+ second delay on first request
            std::thread::spawn(|| {
                eprintln!("[STARTUP] Pre-warming Ollama model...");
                let client = reqwest::blocking::Client::builder()
                    .timeout(std::time::Duration::from_secs(120))
                    .build();

                if let Ok(client) = client {
                    let res = client
                        .post("http://localhost:11434/api/generate")
                        .json(&serde_json::json!({
                            "model": "qwen2.5-coder:1.5b",
                            "prompt": "hello",
                            "stream": false,
                            "options": {"num_predict": 1}
                        }))
                        .send();

                    match res {
                        Ok(_) => eprintln!("[STARTUP] Ollama model pre-warmed and ready"),
                        Err(e) => eprintln!("[STARTUP] Ollama pre-warm failed (non-fatal): {}", e),
                    }
                }
            });

            // Start test file watcher for headless testing
            std::thread::spawn(|| {
                use std::path::Path;
                use std::fs;
                use std::time::Duration;

                let command_file = Path::new("/tmp/sam_test_command.json");
                let result_file = Path::new("/tmp/sam_test_results.json");
                let mut last_modified = std::time::SystemTime::UNIX_EPOCH;

                eprintln!("[TEST] Test file watcher started. Watching: {:?}", command_file);

                loop {
                    std::thread::sleep(Duration::from_millis(200));

                    if command_file.exists() {
                        if let Ok(metadata) = fs::metadata(command_file) {
                            if let Ok(modified) = metadata.modified() {
                                if modified > last_modified {
                                    last_modified = modified;

                                    // Read command
                                    if let Ok(content) = fs::read_to_string(command_file) {
                                        if let Ok(cmd) = serde_json::from_str::<serde_json::Value>(&content) {
                                            let command = cmd.get("command").and_then(|v| v.as_str()).unwrap_or("");
                                            eprintln!("[TEST] Received command: {}", command);

                                            // Execute test command in tokio runtime
                                            let rt = tokio::runtime::Runtime::new().unwrap();
                                            let result = rt.block_on(async {
                                                match command {
                                                    "test_run_suite" => {
                                                        let summary = crate::scaffolding::run_and_store_tests().await;
                                                        serde_json::json!({
                                                            "summary": summary,
                                                            "timestamp": std::time::SystemTime::now()
                                                                .duration_since(std::time::UNIX_EPOCH)
                                                                .unwrap()
                                                                .as_millis()
                                                        })
                                                    },
                                                    "test_run_smoke" => {
                                                        let summary = crate::scaffolding::run_smoke_test().await;
                                                        serde_json::json!({
                                                            "summary": summary,
                                                            "timestamp": std::time::SystemTime::now()
                                                                .duration_since(std::time::UNIX_EPOCH)
                                                                .unwrap()
                                                                .as_millis()
                                                        })
                                                    },
                                                    "test_run_single" => {
                                                        let args = cmd.get("args").cloned().unwrap_or_default();
                                                        let case = serde_json::from_value::<crate::scaffolding::TestCase>(args)
                                                            .unwrap_or_else(|_| crate::scaffolding::TestCase {
                                                                name: "Custom".to_string(),
                                                                input: "test".to_string(),
                                                                expected_path: None,
                                                                expected_contains: vec![],
                                                                expected_not_contains: vec![],
                                                                should_sanitize: false,
                                                                expected_sensitivity: None,
                                                                timeout_ms: 5000,
                                                            });
                                                        let result = crate::scaffolding::run_single_test(&case).await;
                                                        let mut json = serde_json::to_value(&result).unwrap_or_default();
                                                        if let Some(obj) = json.as_object_mut() {
                                                            obj.insert("timestamp".to_string(), serde_json::json!(
                                                                std::time::SystemTime::now()
                                                                    .duration_since(std::time::UNIX_EPOCH)
                                                                    .unwrap()
                                                                    .as_millis()
                                                            ));
                                                        }
                                                        json
                                                    },
                                                    _ => serde_json::json!({
                                                        "error": format!("Unknown command: {}", command),
                                                        "timestamp": std::time::SystemTime::now()
                                                            .duration_since(std::time::UNIX_EPOCH)
                                                            .unwrap()
                                                            .as_millis()
                                                    })
                                                }
                                            });

                                            // Write result
                                            if let Ok(json) = serde_json::to_string_pretty(&result) {
                                                let _ = fs::write(result_file, json);
                                                eprintln!("[TEST] Results written to {:?}", result_file);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            spawn_pty,
            send_input,
            resize_pty,
            read_pty,
            close_pty,
            start_pty_output_stream,
            ai_query,
            ai_query_stream,
            execute_shell,
            read_file,
            write_file,
            list_directory_tree,
            list_directory,
            current_working_dir,
            send_test_message,
            send_user_message,
            get_conversation_state,
            test_phase2_workflow,
            test_phase3_workflow,
            create_batch,
            get_batches,
            approve_batch,
            run_batch,
            get_autonomy_settings,
            update_autonomy_settings,
            set_batch_dependency,
            rollback_batch,
            telemetry_insert_event,
            telemetry_query_recent,
            telemetry_export_csv,
            phase4_trigger_trainer,
            policy_list_rules,
            policy_propose_diff,
            policy_list_suggestions,
            policy_apply_suggestion,
            policy_rollback,
            policy_reject_suggestion,
            phase5_generate_suggestions,
            agent_register,
            agent_update,
            agent_set_status,
            agent_list,
            agent_unregister,
            phase6_create_plan,
            phase6_get_plan,
            phase6_get_pending_plans,
            phase6_update_plan_status,
            phase6_update_plan_index,
            phase6_delete_plan,
            get_monitoring_events,
            clear_monitoring_phase,
            clear_monitoring_all,
            start_scheduler,
            stop_scheduler,
            run_phase1_6_auto,
            query_ollama_stream,
            query_ollama,
            query_ollama_chat,
            list_ollama_models,
            save_session,
            load_session,
            get_app_version,
            // New features for Warp/Claude Code parity
            edit_file,
            web_fetch,
            get_shell_completions,
            get_ai_completion,
            init_project_context,
            load_project_context_cmd,
            // SSH support
            ssh_connect_password,
            ssh_connect_key,
            ssh_send_input,
            ssh_read_output,
            ssh_resize,
            ssh_disconnect,
            ssh_list_sessions,
            // Glob and Grep
            glob_files,
            grep_files,
            // Scaffolded Agent (Claude-like capabilities)
            start_agent_task,
            list_agent_models,
            check_ollama_status,
            // Debug logging
            debug_log,
            execute_agent_tool,
            // Unified Agent (24/7 guaranteed success)
            start_unified_task,
            resume_unified_task,
            list_unified_tasks,
            get_unified_task_status,
            // Intelligence Engine (instant, no AI)
            intelligence_run,
            intelligence_parse,
            // Intelligence V2 (comprehensive coverage, ~150 task types)
            intelligence_v2_run,
            intelligence_v2_parse,
            // Session state (memory without AI)
            get_session_state,
            get_history,
            get_last_command,
            add_alias,
            detect_project,
            get_error_suggestion,
            // Smart edit (Claude Code style)
            smart_edit,
            edit_line,
            insert_after_line,
            delete_lines,
            regex_replace,
            undo_edit,
            create_file_safe,
            append_to_file,
            // Workflows (Warp-style saved command sequences)
            workflow_create,
            workflow_add_step,
            workflow_list,
            workflow_get,
            workflow_resolve,
            workflow_delete,
            workflow_builtins,
            // Multi-edit (atomic multi-file transactions)
            multi_edit_begin,
            multi_edit_add,
            multi_edit_commit,
            multi_edit_rollback,
            multi_edit_list,
            // Todo tracker (Claude Code style task tracking)
            todo_add,
            todo_add_many,
            todo_set_status,
            todo_list,
            todo_stats,
            todo_remove,
            todo_clear,
            todo_clear_completed,
            // Command palette (Cmd+K fuzzy search)
            palette_search,
            palette_search_files,
            palette_update_files,
            palette_record_usage,
            palette_recent,
            // Pane manager (split panes / tabs)
            pane_new_tab,
            pane_close_tab,
            pane_switch_tab,
            pane_list_tabs,
            pane_split,
            pane_close,
            pane_focus,
            pane_focus_next,
            pane_focus_prev,
            pane_active,
            pane_set_pty,
            pane_layout,
            pane_sizes,
            // AI Options (4 systems)
            ai_route_request,
            ai_routing_stats,
            embedding_index_directory,
            embedding_search,
            embedding_search_name,
            embedding_stats,
            embedding_save,
            embedding_load,
            template_list,
            template_get,
            template_search,
            template_fill,
            template_generate_prompt,
            model_select,
            model_stats,
            model_list_available,
            model_mark_loaded,
            model_mark_unloaded,
            model_record_result,
            model_get_idle,
            // Orchestrator (central integration)
            orchestrate_request,
            orchestrate_stats,
            // Browser bridge
            poll_bridge_response,
            get_bridge_tasks,
            queue_browser_task,
            // Background tasks
            background_tasks_list,
            background_tasks_running,
            background_task_get,
            background_task_cancel,
            background_tasks_summary,
            background_tasks_formatted,
            background_index_directory,
            // Streaming
            stream_create_session,
            stream_poll,
            stream_close_session,
            stream_read_file,
            stream_search,
            // Hooks system (extensibility)
            hooks_init,
            hooks_list,
            hooks_register,
            hooks_unregister,
            hooks_set_enabled,
            hooks_run,
            // Skills system (slash commands)
            skills_list,
            skills_search,
            skills_parse,
            skills_execute,
            skills_execute_raw,
            // MCP (Model Context Protocol)
            mcp_add_server,
            mcp_connect,
            mcp_list_tools,
            mcp_call_tool,
            mcp_load_config,
            mcp_list_servers,
            // Speed Cache
            cache_get_stats,
            cache_check,
            cache_clear_all,
            cache_hit_rate,
            // Web Search
            cmd_web_search,
            cmd_web_fetch,
            // Config Files
            cmd_load_project_config,
            cmd_get_instructions,
            cmd_get_rules,
            // Parallel Agents
            cmd_execute_parallel,
            cmd_create_parallel_task,
            cmd_cancel_parallel_agents,
            cmd_parallel_stats,
            // Autocomplete
            cmd_get_completions,
            cmd_add_completion_history,
            cmd_autocomplete_stats,
            // Hot Reload
            cmd_watch_directory,
            cmd_unwatch_directory,
            cmd_start_watcher,
            cmd_stop_watcher,
            cmd_reindex,
            cmd_indexer_stats,
            cmd_watcher_running,
            // Autonomy Controls
            cmd_set_autonomy_level,
            cmd_get_autonomy_level,
            cmd_requires_approval,
            cmd_approve_action,
            cmd_dispatch_mode_on,
            cmd_dispatch_mode_off,
            cmd_is_dispatch_mode,
            cmd_autonomy_config,
            // Subagents
            cmd_create_delegation_plan,
            cmd_execute_delegation_plan,
            cmd_get_delegation_plan,
            cmd_cancel_delegation_plan,
            cmd_subagent_stats,
            // Privacy & Task Execution
            execute_action,
            // Test Harness
            test_run_suite,
            test_run_smoke,
            test_run_single,
            test_status,
            test_get_cases,
            test_run_custom,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}
