import type { Plugin } from "@opencode-ai/plugin"
import { readFileSync } from "node:fs"
import { join } from "node:path"

type AgenticPluginConfig = {
  settings?: any
}

function telegramApiBaseUrl(): string {
  return process.env.OPENCODE_TELEGRAM_API_BASE_URL || "https://api.telegram.org"
}

function telegramUrl(botToken: string, method: string): string {
  return `${telegramApiBaseUrl()}/bot${botToken}/${method}`
}

function redactSecret(value: unknown): string {
  const text = String(value)
  const telegram = currentTelegramConfig
  const token = telegram?.botToken
  const chatId = telegram?.chatId
  return [token, chatId].filter(Boolean).reduce((output, secret) => output.split(secret as string).join("[redacted]"), text)
}

function readAgenticConfig(directory: string): AgenticPluginConfig {
  const configPath = join(directory, ".agentic.json")
  try {
    return JSON.parse(readFileSync(configPath, "utf-8")) as AgenticPluginConfig
  } catch {
    return {}
  }
}

let currentTelegramConfig

export const TelegramNotificationPlugin: Plugin = async ({ $, client, directory }) => {
  const config = readAgenticConfig(directory)
  const telegram = config.settings?.opencode_plugins?.telegram
  currentTelegramConfig = telegram
  const botToken = telegram?.botToken
  const chatId = telegram?.chatId

  if (!telegram?.enabled || !botToken || !chatId) {
    return {}
  }

  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        const sessionID = event.properties.sessionID
        let messageText = "✅ Задача завершена"
        let fullText = ""

        try {
          const sessionResult = await client.session.get({ path: { id: sessionID } })
          const session = sessionResult.data

          if (!sessionResult.error && session) {
            messageText = `✅ ${session.title || "Задача завершена"}`

            if (session.summary) {
              messageText += `\n📊 +${session.summary.additions} -${session.summary.deletions} в ${session.summary.files} файл(ах)`
            }

            const messagesResult = await client.session.messages({ path: { id: sessionID } })
            if (!messagesResult.error && messagesResult.data?.length) {
              const lastMessage = messagesResult.data[messagesResult.data.length - 1]
              const textParts = lastMessage.parts?.filter(p => p.type === "text") || []
              fullText = textParts.map(p => (p as any).text).join("")
            }
          }
        } catch (e) {
          await $`echo "Error: ${redactSecret(e)}" >> ${directory}/.opencode/telegram-debug.log`
        }

        try {
          if (fullText.length >= 4096) {
            const formData = new FormData()
            formData.append("chat_id", chatId)
            formData.append(
              "document",
              new Blob([fullText], { type: "text/markdown" }),
              `response-${sessionID.slice(0, 8)}.md`
            )

            await fetch(
              telegramUrl(botToken, "sendDocument"),
              { method: "POST", body: formData }
            )

            const shortText = fullText.slice(0, 3000)
            await fetch(
              telegramUrl(botToken, "sendMessage"),
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  chat_id: chatId,
                  text: `${messageText}\n\nПолный ответ в attachment (${fullText.length} символов):\n\n${shortText}...`
                })
              }
            )
          } else {
            const textToSend = fullText
              ? `${messageText}\n\n${fullText}`
              : messageText

            await fetch(
              telegramUrl(botToken, "sendMessage"),
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  chat_id: chatId,
                  text: textToSend.slice(0, 4096)
                })
              }
            )
          }
        } catch {}
      }
    },
  }
}
