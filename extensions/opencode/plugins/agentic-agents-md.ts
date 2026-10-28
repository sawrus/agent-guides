/** Agentic `--agents-md keep` guidance for the OpenCode V2 plugin API (2.0.28+). */
import { Plugin } from "@opencode/plugin";
import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";

// With `agentic install --agents-md keep` the project owns root AGENTS.md, and the generated guidance lives in
// .agent/AGENTS.md. OpenCode 2.0.x loads only the global and the project AGENTS.md as instructions and ignores
// `instructions` in its config, so this plugin adds .agent/AGENTS.md as one system part to every request,
// the way AGENTS.md itself reaches the model. agentic installs the plugin only in keep mode.
export default Plugin.define({
  id: "agentic-agents-md",
  async setup(ctx) {
    const file = join(ctx.location.directory, ".agent", "AGENTS.md");
    let cached: { mtime: number; text: string } | undefined;

    function guidance(): string | undefined {
      try {
        const mtime = statSync(file).mtimeMs;
        if (cached?.mtime !== mtime) {
          let text = readFileSync(file, "utf8").replace(/\r\n/g, "\n");
          // Drop the agentic metadata block; the model needs only the guidance.
          if (text.startsWith("---\n")) {
            const end = text.indexOf("\n---\n", 4);
            if (end > 0) text = text.slice(end + 5);
          }
          cached = { mtime, text: text.trim() };
        }
        return cached.text || undefined;
      } catch {
        return undefined;
      }
    }

    const disposable = await ctx.session.hook("context", async (event) => {
      const text = guidance();
      if (text) event.system.push({ type: "text", text: `Instructions from: ${file}\n${text}` });
    });

    return async () => {
      await disposable.dispose().catch(() => {});
    };
  },
});
