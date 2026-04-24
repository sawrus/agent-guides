import type { Plugin } from "@opencode-ai/plugin"
import { mkdir, readFile, writeFile } from "node:fs/promises"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { tmpdir } from "node:os"
import { spawn } from "node:child_process"

interface ModelResult {
  model: string
  status: "passed" | "failed"
  error?: string
}

interface ModelCheckerConfig {
  models: string[]
  timeoutMs: number
  concurrency: number
  prompt: string
  probeDir: string
}

type CommandResult = {
  code: number | null
  output: string
  timedOut: boolean
  durationMs: number
}

type AgenticPluginConfig = {
  modelChecker?: {
    enabled?: boolean
  }
}

function readAgenticConfig(): AgenticPluginConfig {
  const configHome = process.env.XDG_CONFIG_HOME || join(process.env.HOME || "", ".config")
  const configPath = join(configHome, "agentic", "opencode-plugins.json")

  try {
    return JSON.parse(readFileSync(configPath, "utf-8")) as AgenticPluginConfig
  } catch {
    return {}
  }
}

async function readModelsJson(projectDir: string): Promise<ModelCheckerConfig> {
  const defaults: ModelCheckerConfig = {
    models: [],
    timeoutMs: 10000,
    concurrency: 3,
    prompt: "Reply with exactly: OK",
    probeDir: tmpdir(),
  }

  try {
    const filePath = join(projectDir, ".opencode", "plugins", "model-checker.json")
    const content = await readFile(filePath, "utf-8")
    const data = JSON.parse(content)
    if (!Array.isArray(data.models)) return defaults

    const models = [...new Set(data.models.map(String).filter(Boolean))]
    const timeoutMs = Number.isFinite(data.timeoutMs)
      ? Math.min(120000, Math.max(1000, Number(data.timeoutMs)))
      : defaults.timeoutMs
    const concurrency = Number.isFinite(data.concurrency)
      ? Math.min(10, Math.max(1, Number(data.concurrency)))
      : defaults.concurrency
    const prompt = typeof data.prompt === "string" && data.prompt.trim() ? data.prompt.trim() : defaults.prompt
    const probeDir = typeof data.probeDir === "string" && data.probeDir.trim() ? data.probeDir.trim() : defaults.probeDir

    return {
      models,
      timeoutMs,
      concurrency,
      prompt,
      probeDir,
    }
  } catch {
    return defaults
  }
}

async function runModelProbe(model: string, prompt: string, timeoutMs: number, probeDir: string): Promise<CommandResult> {
  return await new Promise((resolve) => {
    const startedAt = Date.now()
    const child = spawn("opencode", ["run", prompt, "-m", model, "--dir", probeDir, "--log-level", "ERROR"], {
      cwd: probeDir,
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        OPENCODE_MODEL_CHECKER_ACTIVE: "1",
      },
    })

    let stdout = ""
    let stderr = ""
    let timedOut = false

    const timer = setTimeout(() => {
      timedOut = true
      child.kill("SIGKILL")
    }, timeoutMs)

    child.stdout.on("data", (chunk: Buffer | string) => {
      stdout += chunk.toString()
    })

    child.stderr.on("data", (chunk: Buffer | string) => {
      stderr += chunk.toString()
    })

    child.on("close", (code) => {
      clearTimeout(timer)
      resolve({
        code,
        timedOut,
        output: `${stdout}\n${stderr}`.toLowerCase(),
        durationMs: Date.now() - startedAt,
      })
    })

    child.on("error", (error) => {
      clearTimeout(timer)
      resolve({
        code: 1,
        timedOut,
        output: String(error).toLowerCase(),
        durationMs: Date.now() - startedAt,
      })
    })
  })
}

async function runModelChecks(
  models: string[],
  prompt: string,
  timeoutMs: number,
  concurrency: number,
  probeDir: string,
): Promise<CommandResult[]> {
  const workers = Math.min(concurrency, models.length)
  const results: CommandResult[] = new Array(models.length)
  let cursor = 0

  await Promise.all(
    Array.from({ length: workers }, async () => {
      while (true) {
        const index = cursor++
        if (index >= models.length) return
        results[index] = await runModelProbe(models[index], prompt, timeoutMs, probeDir)
      }
    }),
  )

  return results
}

function classifyResult(model: string, probe: CommandResult): ModelResult {
  if (probe.timedOut) return { model, status: "failed", error: "timeout" }

  if (probe.output.includes("quota") || probe.output.includes("insufficient") || probe.output.includes("429")) {
    return { model, status: "failed", error: "quota" }
  }

  if (probe.code !== 0) {
    if (/(\b4\d\d\b|\b5\d\d\b)/.test(probe.output)) {
      return { model, status: "failed", error: "provider error" }
    }
    return { model, status: "failed", error: `exit code ${probe.code ?? "null"}` }
  }

  if (!probe.output.includes("ok")) {
    return { model, status: "failed", error: "unexpected response" }
  }

  return { model, status: "passed" }
}

function printLists(passed: ModelResult[], failed: ModelResult[]) {
  console.log("\npassed_models:")
  for (const model of passed) {
    console.log(`- ${model.model}`)
  }

  console.log("\nfailed_models:")
  for (const model of failed) {
    console.log(`- ${model.model}${model.error ? ` (${model.error})` : ""}`)
  }
}

function formatTelegramMessage(passed: ModelResult[], failed: ModelResult[], selected: string): string {
  const passedText = passed.length ? passed.map((x) => `• ${x.model}`).join("\n") : "(none)"
  const failedText = failed.length
    ? failed.map((x) => `• ${x.model}${x.error ? ` (${x.error})` : ""}`).join("\n")
    : "(none)"

  return [
    "<b>LLM availability check</b>",
    "",
    `<b>passed_models (${passed.length})</b>`,
    passedText,
    "",
    `<b>failed_models (${failed.length})</b>`,
    failedText,
    "",
    `<b>selected model:</b> ${selected}`,
  ].join("\n")
}

async function sendTelegram(message: string) {
  const token = process.env.OPENCODE_TELEGRAM_BOT_TOKEN
  const chatID = process.env.OPENCODE_TELEGRAM_CHAT_ID
  if (!token || !chatID) return

  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatID,
        text: message,
        parse_mode: "HTML",
      }),
    })
  } catch {
    // no-op
  }
}

async function regenerateOpencodeJson(projectDir: string, selected: string, passed: string[]) {
  const filePath = join(projectDir, ".opencode", "opencode.json")
  try {
    const content = await readFile(filePath, "utf-8")
    const config = JSON.parse(content)

    if (!config.agent || typeof config.agent !== "object") return

    for (const [agentName, agentConfig] of Object.entries<any>(config.agent)) {
      if (!agentConfig || typeof agentConfig !== "object") continue
      if (agentConfig.mode !== "subagent") continue

      config.agent[agentName].model = selected
    }

    await writeFile(filePath, `${JSON.stringify(config, null, 2)}\n`, "utf-8")
  } catch {
    // no-op
  }
}

export const ModelCheckerPlugin: Plugin = async ({ directory }) => {
  const config = readAgenticConfig()
  if (!config.modelChecker?.enabled) {
    return {}
  }

  if (process.env.OPENCODE_MODEL_CHECKER_ACTIVE === "1") {
    return {}
  }

  if (process.argv[2] === "run") {
    return {}
  }

  async function runChecks() {
    const config = await readModelsJson(directory)
    const { models, prompt, timeoutMs, concurrency, probeDir } = config
    if (!models.length) return

    await mkdir(probeDir, { recursive: true })

    console.log("\nStarting LLM model availability check...")
    console.log(`- models: ${models.length}, concurrency: ${Math.min(concurrency, models.length)}, timeout: ${timeoutMs}ms`)
    const results: ModelResult[] = []
    const probes = await runModelChecks(models, prompt, timeoutMs, concurrency, probeDir)
    for (const [index, model] of models.entries()) {
      const probe = probes[index]
      const result = classifyResult(model, probe)
      results.push(result)
      console.log(
        `- checking ${model}... ${result.status === "passed" ? "OK" : `FAIL (${result.error})`} (${probe.durationMs}ms)`,
      )
    }

    const passedModels = results.filter((x) => x.status === "passed")
    const failedModels = results.filter((x) => x.status === "failed")
    const selected = passedModels[0]?.model ?? "none"

    printLists(passedModels, failedModels)
    console.log(`\nselected_model: ${selected}`)

    if (selected !== "none") {
      await regenerateOpencodeJson(directory, selected, passedModels.map((x) => x.model))
    }

    await sendTelegram(formatTelegramMessage(passedModels, failedModels, selected))
  }

  await runChecks()

  return {}
}
