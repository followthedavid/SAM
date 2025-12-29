// Flag that tells the main app to run automated commands after window creation
function maybeRunInteractive(app) {
  if (process.env.WARP_OPEN_INTERACTIVE_SMOKE !== '1') return false;
  
  // Set global flag for main app to pick up
  global.__WARP_OPEN_INTERACTIVE_MODE = true;
  return false; // Don't exit here, let main app handle it
}

function maybeRunInteractive(app){
  try { return !!runInteractiveOnce(app); } catch { return false; }
}

module.exports = { maybeRunInteractive };