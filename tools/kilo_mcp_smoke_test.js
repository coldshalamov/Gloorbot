import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const serverPath = "C:\\Users\\User\\.claude\\mcp-servers\\kilo-cli-mcp\\index.js";

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
  let pending = new Map();

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
    clientInfo: { name: "kilo-mcp-smoke", version: "0.0.1" },
  });
  send(proc, { jsonrpc: "2.0", method: "notifications/initialized", params: {} });

  const tools = await request(2, "tools/list", {});
  console.log("tools/list:", JSON.stringify(tools.result?.tools?.map((t) => t.name)));

  const call = await request(3, "tools/call", {
    name: "kilo_task",
    arguments: {
      prompt: "Print OK and exit.",
      mode: "ask",
      timeoutSeconds: 5,
      waitSeconds: 0,
      yolo: true,
    },
  });
  console.log("tools/call:", call.result?.content?.[0]?.text?.slice(0, 300) || "");

  // If the task is async, try parsing jobId and cancel to avoid orphaned processes.
  try {
    const parsed = JSON.parse(call.result?.content?.[0]?.text || "{}");
    if (parsed.jobId) {
      const cancel = await request(4, "tools/call", {
        name: "kilo_task_cancel",
        arguments: { jobId: parsed.jobId },
      });
      console.log("cancel:", cancel.result?.content?.[0]?.text || "");
    }
  } catch {}

  proc.kill();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
