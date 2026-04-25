import { FormEvent, useEffect, useState } from 'react'
import { Bell, Palette, ShieldAlert } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { terminalApi } from '../services/terminalApi'
import { BirdeyeTheme, useTheme } from '../contexts/ThemeContext'
import ConnectWalletButton from '../components/terminal/ConnectWalletButton'
import { useToast } from '../contexts/ToastContext'

const themeOptions: Array<{ id: BirdeyeTheme; title: string; description: string }> = [
  { id: 'sunburst', title: 'Sunburst', description: 'Warm logo orange with gold highlights' },
  { id: 'ember', title: 'Ember', description: 'Sharper coral/orange energy' },
  { id: 'tide', title: 'Tide', description: 'Teal-forward palette pulled from the logo mark' },
  { id: 'midnight', title: 'Midnight', description: 'Cool blue accent with a darker read' },
]

const themeSwatches: Record<BirdeyeTheme, string> = {
  sunburst: '#ff8f40',
  ember: '#ff7043',
  tide: '#40c5b6',
  midnight: '#698aff',
}

const SettingsView = () => {
  const { user, isAuthenticated } = useAuth()
  const { theme, setTheme } = useTheme()
  const { pushToast } = useToast()
  const [alertMethod, setAlertMethod] = useState<'webhook' | 'dm'>('webhook')
  const [discordWebhookUrl, setDiscordWebhookUrl] = useState('')
  const [discordUserId, setDiscordUserId] = useState('')
  const [testingAlert, setTestingAlert] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      setAlertMethod('webhook')
      setDiscordWebhookUrl('')
      setDiscordUserId('')
      return
    }

    const run = async () => {
      try {
        const payload = await terminalApi.getSettings()
        setDiscordWebhookUrl(payload.discord_webhook_url ?? '')
        setDiscordUserId(payload.discord_user_id ?? '')
        
        // Determine which method the user has set up
        if (payload.discord_user_id) {
          setAlertMethod('dm')
        } else if (payload.discord_webhook_url) {
          setAlertMethod('webhook')
        }
      } catch (err) {
        pushToast(err instanceof Error ? err.message : 'Failed to load settings', 'error')
      }
    }

    void run()
  }, [isAuthenticated])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      await terminalApi.updateSettings({
        discord_webhook_url: discordWebhookUrl,
        discord_user_id: discordUserId,
      })
      pushToast('Settings saved successfully.', 'success')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save settings'
      pushToast(msg, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleTestAlert = async () => {
    setTestingAlert(true)
    try {
      const testPayload = 
        alertMethod === 'webhook'
          ? { discord_webhook_url: discordWebhookUrl }
          : { discord_user_id: discordUserId }

      await terminalApi.sendTestAlert(testPayload)

      pushToast('Test alert sent. Check Discord.', 'success')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to send test alert'
      pushToast(msg, 'error')
    } finally {
      setTestingAlert(false)
    }
  }

  return (
    <section className="panel h-full p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
      <p className="panel-title">Settings</p>
      <h1 className="font-display text-2xl text-zinc-100">Terminal Preferences</h1>

      <div className="mt-8 space-y-4">
        <div className="rounded-2xl border-2 border-line bg-zinc-900/35 p-5 shadow-neon max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0 max-md:shadow-none">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="mb-1 text-xs uppercase tracking-[0.18em] text-zinc-500">Theme Palette</p>
              <p className="text-sm text-zinc-300">Pick a logo-derived palette for the dashboard chrome and wallet controls.</p>
            </div>
            <Palette className="h-5 w-5 text-neonOrange" />
          </div>

          <div className="mt-4 grid gap-2 md:grid-cols-2">
            {themeOptions.map((option) => {
              const selected = theme === option.id
              return (
                <button
                  key={option.id}
                  onClick={() => setTheme(option.id)}
                  className={`rounded-xl border p-3 text-left transition ${
                    selected
                      ? 'border-neonOrange/70 bg-neonOrange/10 shadow-neon'
                      : 'border-line bg-black/20 hover:border-neonOrange/40 hover:bg-neonOrange/5'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-display text-sm text-zinc-100">{option.title}</p>
                    <span className="h-3 w-3 rounded-full border border-white/20" style={{ background: themeSwatches[option.id] }} />
                  </div>
                  <p className="mt-1 text-xs text-zinc-400">{option.description}</p>
                </button>
              )
            })}
          </div>
        </div>

        <div className="rounded-2xl border-2 border-line bg-zinc-900/35 p-5 shadow-neon max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0 max-md:shadow-none">
          <div className="mb-2 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-neonOrange" />
            <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Wallet Identity</p>
          </div>
          {!isAuthenticated || !user ? (
            <div className="rounded-2xl border border-neonOrange/25 bg-neonOrange/8 p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-sm text-zinc-200">Sign in with your wallet to unlock alert creation, Discord destination settings, and the alerts manager.</p>
              <p className="mt-1 text-xs text-zinc-400">Connect a wallet in the top bar, then press Sign In.</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <ConnectWalletButton />
                <span className="text-xs text-zinc-500">You can also connect right from here.</span>
              </div>
            </div>
          ) : (
            <p className="font-mono text-sm text-zinc-200">{user.wallet_address}</p>
          )}
        </div>

        {isAuthenticated && user && (
          <form onSubmit={handleSubmit} className="rounded-2xl border-2 border-line bg-zinc-900/35 p-5 space-y-4 shadow-neon max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0 max-md:shadow-none">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-neonOrange" />
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">How Should We Alert You?</p>
            </div>

            {/* Alert Method Toggle */}
            <div className="flex gap-2 rounded-lg border border-line/50 bg-black/20 p-2">
              <button
                type="button"
                onClick={() => setAlertMethod('webhook')}
                className={`flex-1 rounded-md px-3 py-2 text-xs font-medium transition ${
                  alertMethod === 'webhook'
                    ? 'border border-neonOrange/50 bg-neonOrange/20 text-neonOrange'
                    : 'border border-transparent text-zinc-400 hover:text-zinc-300'
                }`}
              >
                🪝 Webhook
              </button>
              <button
                type="button"
                onClick={() => setAlertMethod('dm')}
                className={`flex-1 rounded-md px-3 py-2 text-xs font-medium transition ${
                  alertMethod === 'dm'
                    ? 'border border-neonOrange/50 bg-neonOrange/20 text-neonOrange'
                    : 'border border-transparent text-zinc-400 hover:text-zinc-300'
                }`}
              >
                💬 Direct Message
              </button>
            </div>

            {/* Webhook Configuration */}
            {alertMethod === 'webhook' && (
              <div className="space-y-2 rounded-lg border border-line/30 bg-neonOrange/5 p-3">
                <label className="block text-xs text-zinc-500">
                  Discord Webhook URL
                  <input
                    value={discordWebhookUrl}
                    onChange={(event) => setDiscordWebhookUrl(event.target.value)}
                    placeholder="https://discord.com/api/webhooks/..."
                    className="mt-1 h-10 w-full rounded-lg border border-line bg-zinc-950/60 px-3 text-sm text-zinc-100 outline-none focus:border-neonOrange/50"
                  />
                </label>
                <p className="text-xs text-zinc-400">
                  📖{' '}
                  <a
                    href="https://support.discord.com/hc/en-us/articles/228383668"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-neonOrange"
                  >
                    How to create a Webhook
                  </a>
                </p>
              </div>
            )}

            {/* Direct Message Configuration */}
            {alertMethod === 'dm' && (
              <div className="space-y-2 rounded-lg border border-line/30 bg-neonOrange/5 p-3">
                <label className="block text-xs text-zinc-500">
                  <span className="inline-flex items-center gap-2">
                    Discord User ID
                    <a
                      href="https://support.discord.com/hc/en-us/articles/206346498"
                      target="_blank"
                      rel="noopener noreferrer"
                      title="How to find your Discord user ID"
                      className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-neonOrange/40 text-[10px] text-neonOrange hover:bg-neonOrange/20"
                    >
                      ?
                    </a>
                  </span>
                  <input
                    value={discordUserId}
                    onChange={(event) => setDiscordUserId(event.target.value)}
                    placeholder="123456789012345678"
                    className="mt-1 h-10 w-full rounded-lg border border-line bg-zinc-950/60 px-3 text-sm text-zinc-100 outline-none focus:border-neonOrange/50"
                  />
                </label>
                <p className="text-xs text-zinc-400">
                  ⚠️ You must share a server with the bot and have allow DMs enabled for this to work.
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line/30 pt-3">
              <button
                type="button"
                onClick={handleTestAlert}
                disabled={
                  testingAlert ||
                  (alertMethod === 'webhook' ? !discordWebhookUrl.trim() : !discordUserId.trim())
                }
                className="rounded-lg border border-neonOrange/30 bg-neonOrange/10 px-3 py-2 text-xs text-neonOrange disabled:border-zinc-600 disabled:bg-zinc-900/20 disabled:text-zinc-500 hover:border-neonOrange/60 hover:bg-neonOrange/15 disabled:cursor-not-allowed"
              >
                {testingAlert ? 'Sending...' : '📨 Send Test Alert'}
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg border border-neonOrange/50 bg-neonOrange/15 px-3 py-2 text-xs text-neonOrange disabled:opacity-60"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </form>
        )}

      </div>
    </section>
  )
}

export default SettingsView
