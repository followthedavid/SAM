#!/usr/bin/env node
/**
 * SAM Test Runner - Headless batch testing via file-based IPC
 *
 * This script writes test commands to a file that SAM monitors,
 * then reads results from the response file.
 */

const fs = require('fs');
const path = require('path');

const COMMAND_FILE = '/tmp/sam_test_command.json';
const RESULT_FILE = '/tmp/sam_test_results.json';
const TIMEOUT_MS = 30000;

// Colors for terminal
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m',
};

function log(color, msg) {
    console.log(`${colors[color]}${msg}${colors.reset}`);
}

function printHeader() {
    console.log('');
    log('blue', '╔══════════════════════════════════════════════════════════════╗');
    log('blue', '║                    SAM TEST RUNNER                           ║');
    log('blue', '╚══════════════════════════════════════════════════════════════╝');
    console.log('');
}

function writeCommand(command, args = {}) {
    const cmd = {
        command,
        args,
        timestamp: Date.now(),
    };
    fs.writeFileSync(COMMAND_FILE, JSON.stringify(cmd, null, 2));
    log('cyan', `Sent command: ${command}`);
}

async function waitForResult(timeout = TIMEOUT_MS) {
    const startTime = Date.now();
    const commandTime = JSON.parse(fs.readFileSync(COMMAND_FILE)).timestamp;

    while (Date.now() - startTime < timeout) {
        if (fs.existsSync(RESULT_FILE)) {
            try {
                const result = JSON.parse(fs.readFileSync(RESULT_FILE));
                if (result.timestamp > commandTime) {
                    return result;
                }
            } catch (e) {
                // File still being written
            }
        }
        await new Promise(r => setTimeout(r, 100));
    }
    throw new Error('Timeout waiting for test results');
}

function printResults(data) {
    if (!data.summary) {
        log('yellow', 'No summary in results');
        console.log(JSON.stringify(data, null, 2));
        return;
    }

    const summary = data.summary;
    console.log('');
    log('blue', '══════════════════════════════════════════════════════════════');

    for (const result of summary.results || []) {
        const status = result.passed ? `${colors.green}✓ PASS` : `${colors.red}✗ FAIL`;
        const name = result.name.padEnd(40);
        const time = `${result.latency_ms}ms`.padStart(8);
        console.log(`${status}${colors.reset} ${name} ${time}`);

        if (!result.passed && result.errors) {
            for (const error of result.errors) {
                console.log(`${colors.red}   └─ ${error}${colors.reset}`);
            }
        }
    }

    log('blue', '══════════════════════════════════════════════════════════════');
    const passColor = summary.failed === 0 ? 'green' : 'red';
    log(passColor, `Total: ${summary.total} | Passed: ${summary.passed} | Failed: ${summary.failed} | Time: ${summary.total_time_ms}ms`);
    console.log('');
}

async function runTests(type = 'full') {
    printHeader();

    // Clean up old files
    if (fs.existsSync(RESULT_FILE)) {
        fs.unlinkSync(RESULT_FILE);
    }

    if (type === 'smoke') {
        log('cyan', 'Running smoke tests...');
        writeCommand('test_run_smoke');
    } else {
        log('cyan', 'Running full test suite...');
        writeCommand('test_run_suite');
    }

    try {
        const result = await waitForResult();
        printResults(result);

        // Save results
        fs.writeFileSync(RESULT_FILE, JSON.stringify(result, null, 2));

        // Return exit code based on results
        if (result.summary && result.summary.failed > 0) {
            process.exit(1);
        }
    } catch (e) {
        log('red', `Error: ${e.message}`);
        log('yellow', 'Make sure SAM is running and watching for test commands.');
        log('yellow', 'SAM should be started with test mode enabled.');
        process.exit(1);
    }
}

async function runSingleTest(input, expectedPath) {
    printHeader();

    if (fs.existsSync(RESULT_FILE)) {
        fs.unlinkSync(RESULT_FILE);
    }

    log('cyan', `Testing: "${input}"`);
    if (expectedPath) {
        log('cyan', `Expected path: ${expectedPath}`);
    }

    writeCommand('test_run_single', {
        name: `Custom: ${input.substring(0, 30)}`,
        input,
        expected_path: expectedPath,
        timeout_ms: 5000,
    });

    try {
        const result = await waitForResult();
        console.log('');

        if (result.passed) {
            log('green', '✓ TEST PASSED');
        } else {
            log('red', '✗ TEST FAILED');
            if (result.errors) {
                for (const e of result.errors) {
                    log('red', `  └─ ${e}`);
                }
            }
        }

        console.log('');
        log('blue', 'Details:');
        console.log(`  Path: ${result.actual_path}`);
        console.log(`  Sanitized: ${result.was_sanitized}`);
        console.log(`  Sensitivity: ${result.sensitivity_level}`);
        console.log(`  Latency: ${result.latency_ms}ms`);

        if (result.sanitized_text) {
            console.log(`  Sanitized to: "${result.sanitized_text}"`);
        }

        console.log('');
        log('blue', 'Output:');
        console.log(result.actual_output.substring(0, 500));

    } catch (e) {
        log('red', `Error: ${e.message}`);
        process.exit(1);
    }
}

// Command line interface
const args = process.argv.slice(2);
const command = args[0] || 'help';

switch (command) {
    case 'full':
        runTests('full');
        break;
    case 'smoke':
        runTests('smoke');
        break;
    case 'single':
        if (!args[1]) {
            log('red', 'Usage: test_runner.js single "input text" [expected_path]');
            process.exit(1);
        }
        runSingleTest(args[1], args[2]);
        break;
    case 'help':
    default:
        console.log(`
SAM Test Runner - Headless batch testing

Usage: node test_runner.js <command> [args]

Commands:
  full              Run full test suite (15 tests)
  smoke             Run quick smoke test (3 tests)
  single "input"    Test a single input
  help              Show this help

Examples:
  node test_runner.js full
  node test_runner.js smoke
  node test_runner.js single "git status" "Deterministic"
  node test_runner.js single "roleplay privately"

Note: SAM must be running with test mode enabled to receive commands.
`);
        break;
}
