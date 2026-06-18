import type { Plugin } from "@opencode-ai/plugin"

export const SoundNotificationPlugin: Plugin = async ({ $ }) => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        try {
          const platform = process.platform
          if (platform === "darwin") {
            await $`afplay /System/Library/Sounds/Glass.aiff`
          } else if (platform === "linux") {
            try {
              await $`aplay /usr/share/sounds/alsa/Front_Center.wav`
            } catch {
              try {
                await $`pw-play /usr/share/sounds/freedesktop/stereo/complete.oga`
              } catch {}
            }
          }
        } catch {}
      }
    },
  }
}
