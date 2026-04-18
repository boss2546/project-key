// TestSprite MCP Runner - Sends JSON-RPC messages to TestSprite MCP via stdio
const { spawn } = require('child_process');

const API_KEY = process.env.API_KEY || "sk-user-fZ7jWch8f__rXMaExYe4sGUTi1yEtBxy_Slj3l7dJMzsZ6eLzupuF0DPJzqsFnj7AyKjt8zVxzIeFvfl5MJiEqCM8xV7opV8IStDTMGisBRpvAMy8vTII_Iz9MqbbygULz4";

const toolName = process.argv[2];
const toolArgs = process.argv[3] ? JSON.parse(process.argv[3]) : {};

const mcp = spawn('npx', ['@testsprite/testsprite-mcp@latest'], {
  env: { ...process.env, API_KEY },
  shell: true,
  stdio: ['pipe', 'pipe', 'pipe']
});

let buffer = '';

mcp.stdout.on('data', (data) => {
  buffer += data.toString();
  // Try to parse each line as JSON
  const lines = buffer.split('\n');
  buffer = lines.pop(); // Keep incomplete line in buffer
  for (const line of lines) {
    if (line.trim()) {
      try {
        const msg = JSON.parse(line.trim());
        if (msg.id === 2) {
          console.log(JSON.stringify(msg, null, 2));
        }
      } catch (e) {
        // Skip non-JSON lines
      }
    }
  }
});

mcp.stderr.on('data', (data) => {
  process.stderr.write(data);
});

mcp.on('close', (code) => {
  // Try to parse remaining buffer
  if (buffer.trim()) {
    try {
      const msg = JSON.parse(buffer.trim());
      if (msg.id === 2) {
        console.log(JSON.stringify(msg, null, 2));
      }
    } catch (e) {}
  }
  process.exit(code);
});

// Send initialize
const initMsg = JSON.stringify({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "antigravity", version: "1.0.0" }
  }
});

const initNotif = JSON.stringify({
  jsonrpc: "2.0",
  method: "notifications/initialized"
});

const toolCall = JSON.stringify({
  jsonrpc: "2.0",
  id: 2,
  method: "tools/call",
  params: {
    name: toolName,
    arguments: toolArgs
  }
});

mcp.stdin.write(initMsg + '\n');
setTimeout(() => {
  mcp.stdin.write(initNotif + '\n');
  setTimeout(() => {
    mcp.stdin.write(toolCall + '\n');
  }, 500);
}, 500);
