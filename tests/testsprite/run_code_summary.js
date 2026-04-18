// Run TestSprite generate_code_summary
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
  if (!str.includes('[testsprite-mcp]') && !str.includes('DeprecationWarning')) {
    process.stderr.write(str);
  }
});

setTimeout(() => {
  mcp.stdin.write(JSON.stringify({
    jsonrpc: "2.0", id: 1, method: "initialize",
    params: { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "antigravity", version: "1.0.0" } }
  }) + '\n');

  setTimeout(() => {
    mcp.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + '\n');
    setTimeout(() => {
      mcp.stdin.write(JSON.stringify({
        jsonrpc: "2.0", id: 2, method: "tools/call",
        params: {
          name: "testsprite_generate_code_summary",
          arguments: { projectRootPath: "c:\\Users\\meuok\\Desktop\\PDB" }
        }
      }) + '\n');
    }, 1000);
  }, 500);
}, 1000);

setTimeout(() => { console.error('Timeout'); process.exit(1); }, 300000);
