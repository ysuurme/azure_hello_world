/**
 * MCP Bridge Wrapper — Redirects console.log to stderr.
 *
 * The @intelligentinternet/gemini-cli-mcp-openai-bridge writes startup logs
 * to stdout via console.log(). MCP protocol requires stdout to be a clean
 * JSON-RPC channel. This wrapper patches console.log/warn/info to use
 * stderr before loading the bridge, keeping the stdio pipes clean.
 */
const { stderr } = require('process');

// Redirect all console output methods to stderr so stdout stays pure JSON-RPC
console.log   = (...args) => stderr.write(args.join(' ') + '\n');
console.info  = (...args) => stderr.write(args.join(' ') + '\n');
console.warn  = (...args) => stderr.write(args.join(' ') + '\n');

// Now load the actual bridge entry point — it inherits the patched console
require(process.argv[2]);
