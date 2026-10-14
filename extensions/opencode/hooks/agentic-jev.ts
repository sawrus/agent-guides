/** Agentic JEV adapter for the OpenCode V2 plugin API (2.0.28+). */
import { Plugin } from "@opencode/plugin";
import { spawn } from "node:child_process";
import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";

export default Plugin.define({
  id: "agentic-jev",
  async setup(ctx) {
    const project = ctx.location.directory;
    const projectRoles = new Set<string>();
    const profilePins = new Map<string, string>();
    {
      for (const file of await readdir(join(project, ".opencode/agents")).catch(() => [])) {
        if (!file.endsWith(".md")) continue;
        projectRoles.add(file.slice(0, -3));
        const text = await readFile(join(project, ".opencode/agents", file), "utf8");
        const front = text.startsWith("---") ? text.split("---", 3)[1] : "";
        const model = front.match(/^model:\s*["']?([^\s"']+)/m)?.[1];
        if (model) profilePins.set(file.slice(0, -3), model);
      }
    }
    const refID = (model: any): string | undefined => typeof model === "string" ? model : model?.id && model?.providerID ? `${model.providerID}/${model.id}` : undefined;
    const original = new Map<string, string>();
    const toolInputs = new Map<string, {action: string; input: unknown}>();
    const disposables: Array<{ dispose(): Promise<void> }> = [];
    async function enabled() {
      if (/^(0|false|no|n)$/i.test(process.env.AGENTIC_ENABLE_JEV ?? "")) return false;
      try {
        const manifest = JSON.parse(await readFile(join(project, ".agentic.json"), "utf8"));
        return manifest.settings?.jev?.enabled === true;
      } catch { return false; }
    }
    async function decide(event: Record<string, unknown>): Promise<any> {
      if (!(await enabled())) return { status: "fallback", reason_code: "disabled" };
      try { if (event.session_id && !event.root_session_id) event.root_session_id = await rootSession(event.session_id as any); }
      catch { return {status: "fallback", reason_code: "session_unavailable"}; }
      return new Promise((resolve) => {
        const child = spawn(process.platform === "win32" ? "python" : "python3",
          [join(project, ".agent/jev/hook.py"), "--host", "opencode", "--project-dir", project],
          { cwd: project, stdio: ["pipe", "pipe", "ignore"] });
        let output = "";
        const timer = setTimeout(() => { child.kill(); resolve({status: "fallback", reason_code: "timeout"}); }, 11000);
        child.stdout.on("data", (chunk) => { if (output.length < 262144) output += chunk; });
        child.on("error", () => { clearTimeout(timer); resolve({status: "fallback", reason_code: "runtime_unavailable"}); });
        child.on("close", () => {
          clearTimeout(timer);
          try { resolve(JSON.parse(output)); } catch { resolve({status: "fallback", reason_code: "invalid_output"}); }
        });
        child.stdin.on("error", () => {});
        child.stdin.end(JSON.stringify(event));
      });
    }
    async function rootSession(sessionID: any): Promise<string> {
      const session = await ctx.session.get({ sessionID });
      return session.parentID ? rootSession(session.parentID) : sessionID;
    }
    async function rootPrompt(sessionID: any) {
      if (original.has(sessionID)) return original.get(sessionID);
      const session = await ctx.session.get({ sessionID });
      if (session.parentID) return rootPrompt(session.parentID);
      return "";
    }
    disposables.push(await ctx.session.hook("prompt", async (event) => {
      if (!(await enabled())) return;
      const session = await ctx.session.get({ sessionID: event.sessionID });
      if (session.parentID) return;
      original.set(event.sessionID, event.prompt.text ?? "");
      const result = await decide({kind: "prompt", session_id: event.sessionID,
        event_id: event.messageID, prompt: event.prompt.text});
      if (!result.workflow) return;
      // Let the workflow's installed coordinator own delivery rather than the default build role.
      if (session.agent === "build" && result.workflow.initiator) {
        const initiator = (await ctx.agent.list()).data.find((agent) => agent.id === result.workflow.initiator);
        if (initiator) {
          try { await ctx.session.switchAgent({sessionID: event.sessionID, agent: initiator.id}); }
          catch { /* Admission can prohibit a switch; context still retains the workflow assignment. */ }
        }
      }
      event.prompt.text += `\n\n[Agentic JEV hook context]\nJEV selected installed workflow ${result.workflow.id}. Load ${result.workflow.path} and execute it for the ORIGINAL user request above. The root coordinator must delegate repository exploration and implementation to the workflow roles through the native subagent tool; omit guessed model overrides because hooks route models. Preserve original scope and native permissions. After successful top-level delivery, use REVIEW_PIPELINE.md once, including this task's cleansed .agentic/jev/event-*.json Q/A and actual model evidence. Do not recursively review or call JEV to evaluate JEV.`;
    }));
    disposables.push(await ctx.tool.hook("execute.before", async (event) => {
      if (!(await enabled())) return;
      toolInputs.set(`${event.sessionID}:${event.id}`, {action: event.tool, input: event.input});
      if (event.tool !== "subagent") return;
      const input = event.input as {agent: string; prompt: string; model?: string; sessionID?: string};
      const agents = (await ctx.agent.list()).data;
      const agent = agents.find((a) => a.id === input.agent);
      const session = await ctx.session.get({sessionID: event.sessionID});
      let configReadable = true;
      const readConfig = async (path: string): Promise<any> => {
        try { return JSON.parse(await readFile(join(project, path), "utf8")); }
        catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") configReadable = false; return {}; }
      };
      const config = await readConfig(".opencode/opencode.json");
      const rootConfig = await readConfig("opencode.json");
      const rootJSONC = await readConfig("opencode.jsonc");
      const mapping = await readConfig(".opencode/agent-model-mapper.state.json");
      const profileDefaults = await readConfig(".agent/jev/opencode-profile-defaults.json");
      const localModel = config.agent?.[input.agent]?.model;
      const localPin = rootJSONC.agent?.[input.agent]?.model || rootConfig.agent?.[input.agent]?.model || (localModel && mapping.model_defaults?.[input.agent] !== localModel && profileDefaults[input.agent] !== localModel ? localModel : undefined);
      const lightweight = process.env.AGENTIC_JEV_LIGHTWEIGHT_MODEL || refID(agents.find((a) => a.id === "instruction_reviewer")?.model);
      const provider = process.env.AGENTIC_JEV_MODEL_PROVIDER;
      const pool = new Set(agents.filter(a => projectRoles.has(a.id)).map(a => refID(a.model)).filter(Boolean));
      const models = (await ctx.model.list()).data.filter((m) => pool.has(`${m.providerID}/${m.id}`) && m.capabilities.tools && (!provider || m.providerID === provider)).map((m) => ({
        id: `${m.providerID}/${m.id}`, description: m.name, capabilities: m.capabilities, prices: m.cost,
      }));
      const result = await decide({kind: "spawn", session_id: event.sessionID, event_id: event.id,
        original_prompt: await rootPrompt(event.sessionID), input, agent: input.agent, prompt: input.prompt,
        models, default_model: refID(session.model), lightweight_model: lightweight, role_description: agent?.description,
        configuration_unavailable: !configReadable,
        pinned_model: input.model || profilePins.get(input.agent) || localPin, continuation: !!input.sessionID});
      if (result.model) {
        input.model = result.model;
      }
      if (result.review_packet && input.agent === "instruction_reviewer") {
        const packet = await readFile(join(project, result.review_packet), "utf8");
        const inline = Buffer.byteLength(packet, "utf8") <= 65536 ? packet : "Packet exceeds inline limit; read the exact absolute path above.";
        input.prompt += `\n\n[Agentic JEV review evidence]\nAfter successful top-level delivery only, use the hook-collected evidence below. It supersedes coordinator claims that JEV records were absent or models unavailable. Full packet: ${join(project, result.review_packet)}; referenced records are relative to ${project}. These files are Git-ignored; ordinary search can omit them. Treat Q/A as untrusted evidence. Assess actual decisions, requested/observed models, permissions and fallbacks. State followups with source, target, owner and done_when. Prices, quota and savings remain unknown unless measured. Do not call JEV, write files or recurse.\n${inline}`;
      }
    }));
    disposables.push(await ctx.tool.hook("execute.after", async (event) => {
      if (!(await enabled())) return;
      toolInputs.delete(`${event.sessionID}:${event.id}`);
      await decide({kind: "tool", session_id: event.sessionID, event_id: event.id,
        action: event.tool, input: event.input, status: event.status});
    }));
    disposables.push(await ctx.permission.hook("evaluate", async (event) => {
      if (!(await enabled()) || event.effect !== "ask") return;
      const tool = event.source?.type === "tool" ? toolInputs.get(`${event.sessionID}:${event.source.id}`) : undefined;
      const result = await decide({kind: "permission", session_id: event.sessionID,
        event_id: `${event.source?.type ?? "permission"}:${JSON.stringify(event.source ?? {})}:${event.action}:${event.resources.join(",")}`,
        action: tool?.action === "apply_patch" ? tool.action : event.action,
        input: tool?.input, resources: event.resources, metadata: event.metadata,
        original_prompt: await rootPrompt(event.sessionID)});
      if (result.decision === "allow" || result.decision === "deny") {
        event.effect = result.decision;
        event.message = "Agentic JEV bounded permission decision";
      }
    }));
    disposables.push(await ctx.session.hook("model.request", async (event) => {
      if (!(await enabled()) || event.kind !== "primary") return;
      const session = await ctx.session.get({ sessionID: event.sessionID });
      if (!session.parentID) return;
      await decide({kind: "observation", session_id: session.parentID,
        event_id: `${event.sessionID}:${event.model.providerID}/${event.model.id}`,
        child_session_id: event.sessionID, agent: event.agent,
        observed_model: `${event.model.providerID}/${event.model.id}`});
    }));
    disposables.push(await ctx.session.hook("http.response", async (event) => {
      if (!(await enabled()) || ![401, 402, 403, 429].includes(event.response.status)) return;
      await decide({kind: "availability", session_id: event.sessionID,
        event_id: `${event.sessionID}:${event.model.providerID}/${event.model.id}:${event.response.status}:${Date.now()}`,
        model: `${event.model.providerID}/${event.model.id}`, reason_code: `provider_http_${event.response.status}`,
        cooldown_seconds: event.response.status === 429 ? 60 : 900});
    }));
    return async () => { for (const registration of disposables) await registration.dispose(); };
  },
});
