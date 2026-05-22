import type { Plugin } from "@opencode-ai/plugin"
import { existsSync, readFileSync } from "node:fs"
import { readdir, readFile } from "node:fs/promises"
import { basename, join } from "node:path"

type AgenticPluginConfig = {
  agentModelMapper?: {
    enabled?: boolean
  }
  settings?: any
}

type Role = {
  name: string
  description: string
  mode: string
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

function readProjectAgenticConfig(directory: string): AgenticPluginConfig {
  try {
    return JSON.parse(readFileSync(join(directory, ".agentic.json"), "utf-8")) as AgenticPluginConfig
  } catch {
    return {}
  }
}

function parseFrontmatter(text: string): Record<string, string> {
  if (!text.startsWith("---\n")) return {}
  const end = text.indexOf("\n---", 4)
  if (end === -1) return {}

  const result: Record<string, string> = {}
  for (const line of text.slice(4, end).split("\n")) {
    const index = line.indexOf(":")
    if (index === -1) continue
    result[line.slice(0, index).trim()] = line.slice(index + 1).trim().replace(/^['"]|['"]$/g, "")
  }
  return result
}

async function readRoles(directory: string): Promise<Role[]> {
  const agentsDir = join(directory, ".opencode", "agents")
  let entries: string[]
  try {
    entries = await readdir(agentsDir)
  } catch {
    return []
  }

  const roles: Role[] = []
  for (const entry of entries.sort()) {
    if (!entry.endsWith(".md")) continue
    const path = join(agentsDir, entry)
    const text = await readFile(path, "utf-8")
    const frontmatter = parseFrontmatter(text)
    roles.push({
      name: basename(entry, ".md"),
      description: frontmatter.description || "OpenCode agent",
      mode: frontmatter.mode || "subagent",
    })
  }
  return roles
}

function readJsonIfExists(path: string): unknown {
  if (!existsSync(path)) return undefined
  try {
    return JSON.parse(readFileSync(path, "utf-8"))
  } catch {
    return undefined
  }
}

function hasCompleteAgentModelMapping(directory: string, roles: Role[]): boolean {
  const state = readJsonIfExists(join(directory, ".opencode", "agent-model-mapper.state.json")) as Record<string, any> | undefined
  if (!state?.configured) return false

  const config = readJsonIfExists(join(directory, ".opencode", "opencode.json")) as Record<string, any> | undefined
  const agents = config?.agent
  if (!agents || typeof agents !== "object") return false
  return roles.every((role) => {
    const agent = agents[role.name]
    return agent && typeof agent === "object" && typeof agent.model === "string" && agent.model.trim().length > 0
  })
}

export const AgentModelMapperPlugin: Plugin = async ({ directory }) => {
  const projectConfig = readProjectAgenticConfig(directory)
  const globalConfig = readAgenticConfig()
  const enabled = projectConfig.settings?.opencode_plugins?.agentModelMapper?.enabled ?? globalConfig.agentModelMapper?.enabled
  if (!enabled) return {}

  const roles = await readRoles(directory)
  if (!roles.length) {
    console.log("agent-model-mapper: skipped because .opencode/agents/*.md was not found")
    return {}
  }

  if (hasCompleteAgentModelMapping(directory, roles)) {
    console.log("agent-model-mapper: skipped because all Agentic roles already have model mappings")
    return {}
  }

  console.log("agent-model-mapper: install-time model mapping is required; run agentic install or agentic tui")
  return {}
}
