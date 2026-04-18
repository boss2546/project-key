// Run TestSprite bootstrap
const { spawn } = require('child_process');

const API_KEY = "sk-user-fZ7jWch8f__rXMaExYe4sGUTi1yEtBxy_Slj3l7dJMzsZ6eLzupuF0DPJzqsFnj7AyKjt8zVxzIeFvfl5MJiEqCM8xV7opV8IStDTMGisBRpvAMy8vTII_Iz9MqbbygULz4";

const mcp = spawn('npx', ['@testsprite/testsprite-mcp@latest'], {
  env: { ...process.env, API_KEY },
  shell: true,
  stdio: ['pipe', 'pipe', 'pipe']
});

let outputBuffer = '';

mcp.stdout.on('data', (data) => {
  outputBuffer += data.toString();
  const lines = outputBuffer.split('\n');
  outputBuffer = lines.pop();
  for (const line of lines) {
    if (line.trim()) {
      try {
        const msg = JSON.parse(line.trim());
        if (msg.id === 2) {
          console.log(JSON.stringify(msg, null, 2));
          setTimeout(() => process.exit(0), 1000);
        }
      } catch (e) {}
    }
  }
});

mcp.stderr.on('data', (data) => {
  const str = data.toString();
  if (!str.includes('[testsprite-mcp]')) {
    process.stderr.write(str);
  }
});

// Send messages with proper sequencing
setTimeout(() => {
  const init = JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "antigravity", version: "1.0.0" }
    }
  });
  mcp.stdin.write(init + '\n');

  setTimeout(() => {
    mcp.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + '\n');

    setTimeout(() => {
      const toolCall = JSON.stringify({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: {
          name: "testsprite_bootstrap",
          arguments: {
            localPort: 8000,
            type: "frontend",
            projectPath: "c:\\Users\\meuok\\Desktop\\PDB",
            testScope: "codebase"
          }
        }
      });
      mcp.stdin.write(toolCall + '\n');
    }, 1000);
  }, 500);
}, 1000);

// Timeout after 120 seconds
setTimeout(() => {
  console.error('Timeout after 120 seconds');
  process.exit(1);
}, 120000);
