import { spawn } from "child_process";

const serverPath =
  "C:\\\\Users\\\\User\\\\.claude\\\\mcp-servers\\\\gemini-tool\\\\gemini-mcp-tool-main\\\\dist\\\\index.js";

function send(proc, msg) {
  proc.stdin.write(JSON.stringify(msg) + "\n");
}

async function main() {
  const proc = spawn("node", [serverPath], {
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
  });

  proc.stderr.on("data", (d) => process.stderr.write(d));

  let buf = "";
  const pending = new Map();

  proc.stdout.on("data", (d) => {
    buf += d.toString();
    while (true) {
      const idx = buf.indexOf("\n");
      if (idx < 0) break;
      const line = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 1);
      if (!line) continue;
      let msg;
      try {
        msg = JSON.parse(line);
      } catch {
        continue;
      }
      if (msg.id && pending.has(msg.id)) {
        pending.get(msg.id)(msg);
        pending.delete(msg.id);
      }
    }
  });

  function request(id, method, params) {
    return new Promise((resolve) => {
      pending.set(id, resolve);
      send(proc, { jsonrpc: "2.0", id, method, params });
    });
  }

  const init = await request(1, "initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "gemini-mcp-smoke", version: "0.0.1" },
  });
  if (!init?.result) throw new Error("initialize failed");
  send(proc, { jsonrpc: "2.0", method: "notifications/initialized", params: {} });

  const tools = await request(2, "tools/list", {});
  console.log(
    "tools/list:",
    JSON.stringify(tools.result?.tools?.map((t) => t.name)),
  );

  const call = await request(3, "tools/call", {
    name: "ask-gemini",
    arguments: {
      prompt: "Reply with exactly: OK",
      model: "gemini-2.5-flash",
    },
  });
  console.log("tools/call:", call.result?.content?.[0]?.text?.slice(0, 300) || "");

  proc.kill();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

