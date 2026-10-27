/** Agentic quality gate for the OpenCode V2 plugin API (2.0.28+). */
import { Plugin } from "@opencode/plugin";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

// Forwards to the shared gate runtime (.agent/gate/gate.py), the same one Claude Code and Codex call
// from native Stop and PreToolUse hooks. Stop: after a root turn succeeds, a failed check comes back as a
// new prompt in the same session. Guard: permission evaluation turns a risky tool call into a denial, or into
// a question to the user for production access (`guard.confirm` in .agent/gate.json).
export default Plugin.define({
  id: "agentic-gate",
  async setup(ctx) {
    const project = ctx.location.directory;
    const script = join(project, ".agent", "gate", "gate.py");
    const python = process.platform === "win32" ? "python" : "python3";
    const controller = new AbortController();
    const parents = new Set<string>();
    const toolInputs = new Map<string, { tool: string; input: unknown }>();
    const disposables: Array<{ dispose(): Promise<void> }> = [];

    function gate(event: "stop" | "guard", payload: Record<string, unknown>): Promise<any> {
      if (!existsSync(script)) return Promise.resolve({});
      return new Promise((resolve) => {
        try {
          const child = spawn(python, [script, "--host", "opencode", "--event", event, "--project-dir", project], { stdio: ["pipe", "pipe", "ignore"] });
          let out = "";
          child.stdout?.on("data", (chunk) => (out += chunk));
          child.on("error", () => resolve({}));
          child.on("close", () => {
            try { resolve(out.trim() ? JSON.parse(out) : {}); } catch { resolve({}); }
          });
          child.stdin?.on("error", () => {});
          child.stdin?.end(JSON.stringify(payload));
        } catch { resolve({}); }
      });
    }

    disposables.push(await ctx.tool.hook("execute.before", async (event) => {
      toolInputs.set(`${event.sessionID}:${event.id}`, { tool: event.tool, input: event.input });
    }));
    disposables.push(await ctx.tool.hook("execute.after", async (event) => {
      toolInputs.delete(`${event.sessionID}:${event.id}`);
    }));
    disposables.push(await ctx.permission.hook("evaluate", async (event) => {
      const tool = event.source?.type === "tool" ? toolInputs.get(`${event.sessionID}:${event.source.id}`) : undefined;
      const input = (tool?.input ?? {}) as Record<string, unknown>;
      const result = await gate("guard", { tool_name: tool?.tool ?? event.action,
        tool_input: { ...input, path: input.filePath ?? input.path ?? event.resources?.[0] } });
      const output = result?.hookSpecificOutput;
      const reason = output?.permissionDecisionReason;
      if (reason) {
        // "ask" never relaxes a stricter decision already made by OpenCode or another plugin.
        if (output?.permissionDecision !== "ask") {
          event.effect = "deny";
          event.message = reason;
        } else if (event.effect !== "deny") {
          event.effect = "ask";
          event.message = reason;
        }
      }
    }));

    (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        try {
          const type = String((event as any).type);
          const data = (event as any).data ?? {};
          if (type === "session.created" && data.parentID) parents.add(data.sessionID);
          // Subagent turns finish inside the root turn; only the root turn is gated.
          if (type !== "session.execution.succeeded" || parents.has(data.sessionID)) continue;
          const result = await gate("stop", { session_id: data.sessionID });
          if (result?.decision === "block" && result.reason) {
            await (ctx.session as any).prompt({ sessionID: data.sessionID, text: result.reason });
          }
        } catch {}
      }
    })().catch(() => {});

    return async () => {
      controller.abort();
      for (const disposable of disposables) await disposable.dispose().catch(() => {});
    };
  },
});
