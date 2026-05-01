#!/usr/bin/env node
/**
 * MCP Stdio-to-HTTP Proxy for Antigravity
 * 
 * Bridges local stdio MCP protocol to remote HTTP MCP server.
 * Reads JSON-RPC from stdin, forwards to remote endpoint, returns via stdout.
 */

const https = require('https');
const http = require('http');

const REMOTE_URL = process.env.MCP_REMOTE_URL || '';

if (!REMOTE_URL) {
  process.stderr.write('ERROR: MCP_REMOTE_URL environment variable is required\n');
  process.exit(1);
}

const parsedUrl = new URL(REMOTE_URL);
const transport = parsedUrl.protocol === 'https:' ? https : http;

// Phase 1.9 — pathname is `/mcp/{secret}`; logging it leaks the bearer token
// to anyone who sees the user's terminal/CI output. Redact before printing.
function redactedPath(p) {
  return p.replace(/\/mcp\/[^/?#]+/, '/mcp/<redacted>');
}

process.stderr.write(`MCP Proxy: → ${parsedUrl.hostname}${redactedPath(parsedUrl.pathname)}\n`);

function forwardRequest(request) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify(request);
    
    const options = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
      path: parsedUrl.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
      },
    };

    const req = transport.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(body);
          resolve(parsed);
        } catch (e) {
          reject(new Error(`Invalid response: ${res.statusCode} - ${body.substring(0, 200)}`));
        }
      });
    });

    req.on('error', (e) => reject(e));
    req.setTimeout(30000, () => {
      req.destroy();
      reject(new Error('Timeout'));
    });

    req.write(postData);
    req.end();
  });
}

// Read all stdin data
let inputBuffer = '';

process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  inputBuffer += chunk;
  
  // Try to process complete JSON lines
  const lines = inputBuffer.split('\n');
  inputBuffer = lines.pop(); // Keep incomplete last line
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    
    let request;
    try {
      request = JSON.parse(trimmed);
    } catch (e) {
      process.stderr.write(`MCP Proxy: Invalid JSON: ${trimmed.substring(0, 100)}\n`);
      continue;
    }

    process.stderr.write(`MCP Proxy: → ${request.method || 'unknown'}\n`);
    
    forwardRequest(request)
      .then((response) => {
        const out = JSON.stringify(response);
        process.stdout.write(out + '\n');
        process.stderr.write(`MCP Proxy: ← OK (${out.length} bytes)\n`);
      })
      .catch((err) => {
        const errorResponse = {
          jsonrpc: '2.0',
          id: request.id || null,
          error: { code: -32603, message: err.message }
        };
        process.stdout.write(JSON.stringify(errorResponse) + '\n');
        process.stderr.write(`MCP Proxy: ← ERROR: ${err.message}\n`);
      });
  }
});

process.stdin.on('end', () => {
  // Process any remaining buffer
  const trimmed = inputBuffer.trim();
  if (trimmed) {
    try {
      const request = JSON.parse(trimmed);
      forwardRequest(request)
        .then((response) => {
          process.stdout.write(JSON.stringify(response) + '\n');
          process.exit(0);
        })
        .catch(() => process.exit(0));
    } catch (e) {
      process.exit(0);
    }
  } else {
    process.exit(0);
  }
});

// Keep alive
process.stdin.resume();
