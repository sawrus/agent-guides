/** Agentic Telegram notifications for the OpenCode V2 plugin API (2.0.28+). */
import { Plugin } from "@opencode/plugin";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

// Forwards OpenCode events to the shared Agentic notifier (.agent/notify/telegram.py).
// The notifier owns enablement, credentials, Markdown rendering and delivery, so
// OpenCode, Claude Code and Codex send the same messages.
export default Plugin.define({
  id: "agentic-telegram",
  async setup(ctx) {
    const project = ctx.location.directory;
    const script = join(project, ".agent", "notify", "telegram.py");
    const python = process.platform === "win32" ? "python" : "python3";
    const controller = new AbortController();
    // State comes from the event stream itself: `opencode run` stops the server right
    // after the turn ends, so there is no time for session reads at that point.
    const parents = new Map<string, string>();
    // Child sessions that started and have not finished; a root turn is final only when none remain.
    const running = new Set<string>();
    const agents = new Map<string, string>();
    const models = new Map<string, unknown>();
    const titles = new Map<string, string>();
    const replies = new Map<string, string>();
    const asked = new Set<string>();

    function notify(event: "stop" | "waiting", payload: Record<string, unknown>) {
      if (!existsSync(script)) return;
      try {
        // Detached so delivery outlives a server that is shutting down.
        const child = spawn(python, [script, "--host", "opencode", "--event", event, "--project-dir", project],
          { stdio: ["pipe", "ignore", "ignore"], detached: true });
        child.on("error", () => {});
        child.unref();
        child.stdin?.on("error", () => {});
        child.stdin?.end(JSON.stringify(payload));
      } catch {}
    }

    function rootOf(id: string): string {
      let current = id;
      for (let depth = 0; depth < 32 && parents.has(current); depth++) current = parents.get(current)!;
      return current;
    }

    function remember(id: string | undefined, data: any) {
      if (!id) return;
      const agent = typeof data.agent === "string" ? data.agent : data.agent?.name ?? data.agent?.id;
      if (typeof agent === "string" && agent) agents.set(id, agent);
      if (data.model) models.set(id, data.model);
    }

    function identity(id: string) {
      const root = rootOf(id);
      return { agent: agents.get(root), model: models.get(root) };
    }

    function finalTurn(root: string): boolean {
      for (const id of running) if (id !== root && rootOf(id) === root) return false;
      return true;
    }

    function waiting(type: string, data: any) {
      if (!data.id || asked.has(data.id)) return;
      asked.add(data.id);
      if (type === "question.asked") {
        const lines = (data.questions ?? []).flatMap((q: any) => [q.question ?? q.header ?? "",
          ...(q.options ?? []).map((o: any) => `- ${o.label}${o.description ? ` — ${o.description}` : ""}`)]);
        notify("waiting", { session_id: data.sessionID, ...identity(data.sessionID),
          message: lines.filter(Boolean).join("\n") || "Агент задал вопрос" });
        return;
      }
      const resources = Array.isArray(data.resources) ? data.resources.join("\n") : "";
      notify("waiting", { session_id: data.sessionID, ...identity(data.sessionID), message: `Нужно разрешение: ${data.action ?? "действие"}`,
        ...(resources ? { tool_input: { command: resources } } : {}) });
    }

    function handle(type: string, data: any) {
      const id = data.sessionID;
      switch (type) {
        case "session.created":
          if (data.parentID) {
            parents.set(id, data.parentID);
            running.add(id);
          }
          if (data.title) titles.set(id, data.title);
          remember(id, data);
          break;
        case "session.agent.selected":
        case "session.model.selected":
        case "session.step.started":
          remember(id, data);
          break;
        case "session.renamed":
          titles.set(id, data.title);
          break;
        case "session.execution.started":
          if (parents.has(id)) running.add(id);
          replies.delete(id);
          break;
        case "session.text.ended":
          // The last text block of the turn is the final answer.
          if (data.text) replies.set(id, data.text);
          break;
        case "session.execution.succeeded":
          // Subagent sessions finish inside the coordinator's turn; report only root sessions.
          if (parents.has(id)) running.delete(id);
          else notify("stop", { session_id: id, title: titles.get(id), last_assistant_message: replies.get(id) ?? "",
            ...identity(id), final: finalTurn(id) });
          replies.delete(id);
          break;
        case "session.execution.failed":
        case "session.execution.interrupted":
          running.delete(id);
          replies.delete(id);
          break;
        case "permission.asked":
        case "question.asked":
          waiting(type, data);
          break;
      }
    }

    (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        try { handle(String((event as any).type), (event as any).data ?? {}); } catch {}
      }
    })().catch(() => {});

    return async () => controller.abort();
  },
});
