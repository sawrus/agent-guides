import type { Plugin } from "@opencode-ai/plugin"

export const TelegramNotificationPlugin: Plugin = async ({ $, client, directory }) => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        const botToken = process.env.OPENCODE_TELEGRAM_BOT_TOKEN
        const chatId = process.env.OPENCODE_TELEGRAM_CHAT_ID

        if (!botToken || !chatId) return

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
          await $`echo "Error: ${e}" >> ${directory}/.opencode/telegram-debug.log`
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
              `https://api.telegram.org/bot${botToken}/sendDocument`,
              { method: "POST", body: formData }
            )

            const shortText = fullText.slice(0, 3000)
            await fetch(
              `https://api.telegram.org/bot${botToken}/sendMessage`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  chat_id: chatId,
                  text: `${messageText}\n\n📎 Полный ответ в attachment (${fullText.length} символов):\n\n${shortText}...`
                })
              }
            )
          } else {
            const textToSend = fullText
              ? `${messageText}\n\n${fullText}`
              : messageText

            await fetch(
              `https://api.telegram.org/bot${botToken}/sendMessage`,
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
