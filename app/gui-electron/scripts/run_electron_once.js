const { spawn } = require('node:child_process');
const path = require('node:path');
const electronPath = require('electron');
const proc = spawn(electronPath, ['.'], {
  cwd: process.cwd(),
  stdio: 'inherit',
  env: { ...process.env }
});
proc.on('exit', (code, sig) => process.exit(code || (sig ? 1 : 0)));