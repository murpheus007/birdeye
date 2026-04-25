import { Activity, Bell, Bookmark, Bot, Github, Radar, Webhook, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'

const alphaCards = [
  {
    icon: Radar,
    title: 'Real-time Radar',
    description:
      'Track every token launch, liquidity shift, and volume spike the moment it happens — no delay, no noise.',
  },
  {
    icon: Bell,
    title: 'Custom Alerts',
    description:
      'Define your own triggers: price movement, whale accumulation, or wallet activity. Get pinged instantly.',
  },
  {
    icon: Activity,
    title: 'Whale Flow',
    description:
      "Follow the smartest wallets on Solana. See where the big players are moving before the crowd catches on.",
  },
]

const webhookSample = `{
  "event": "whale_buy",
  "token": "BONK",
  "wallet": "Fg6P...x9rW",
  "amount_usd": 142500,
  "timestamp": "2026-04-23T01:15:22Z",
  "chain": "solana"
}`

const LandingView = () => {
  return (
    <div className="min-h-screen bg-[#050505] font-body text-zinc-100">
      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4 text-center">
        {/* Ambient glow */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 70% 55% at 50% 0%, rgba(255,140,0,0.13) 0%, transparent 70%)',
          }}
        />
        {/* Grid overlay */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,140,0,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,140,0,0.04) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />

        <div className="relative z-10 max-w-3xl">
          <div className="mb-8 flex items-center justify-center">
            <div className="relative flex h-36 w-36 items-center justify-center rounded-full border-2 border-neonOrange/50 bg-black shadow-[0_0_36px_rgba(255,140,0,0.28)]">
              <div className="flex animate-spin items-center justify-center gap-4" style={{ animationDuration: '10s' }}>
                {/* Logo 1 container with border ring */}
                <div className="flex h-20 w-20 items-center justify-center rounded-full border border-neonOrange/40 bg-black/80">
                  <img src="/birdeyeradarlogo.png" alt="Birdeye Radar" className="h-16 w-16 object-center" />
                </div>
                {/* Logo 2 container with border ring */}
                <div className="flex h-20 w-20 items-center justify-center rounded-full border border-neonOrange/40 bg-black/80">
                  <img src="/birdeye-logo.png" alt="Birdeye" className="h-16 w-16 object-contain rounded-full" />
                </div>
              </div>
            </div>
          </div>

          <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#FF8C00]/30 bg-[#FF8C00]/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-[#FF8C00]">
            <Zap className="h-3 w-3" />
            Powered by Birdeye
          </span>

          <h1 className="mb-6 font-display text-5xl font-bold leading-[1.1] tracking-tight text-white md:text-7xl">
            Solana Intelligence,{' '}
            <span
              className="relative"
              style={{
                color: '#FF8C00',
                textShadow: '0 0 40px rgba(255,140,0,0.45)',
              }}
            >
              Refined.
            </span>
          </h1>

          <p className="mx-auto mb-10 max-w-xl text-base leading-relaxed text-zinc-400 md:text-lg">
            Professional-grade market radar, whale tracking, and real-time alerts — all in one
            terminal built for serious Solana traders.
          </p>

          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              to="/radar"
              className="group relative inline-flex items-center gap-2 rounded-xl px-8 py-4 text-sm font-semibold text-black transition-all duration-200"
              style={{
                background: '#FF8C00',
                boxShadow: '0 0 0 1px rgba(255,140,0,0.4), 0 0 32px rgba(255,140,0,0.3)',
              }}
              onMouseEnter={(e) => {
                ;(e.currentTarget as HTMLElement).style.boxShadow =
                  '0 0 0 1px rgba(255,140,0,0.7), 0 0 48px rgba(255,140,0,0.45)'
              }}
              onMouseLeave={(e) => {
                ;(e.currentTarget as HTMLElement).style.boxShadow =
                  '0 0 0 1px rgba(255,140,0,0.4), 0 0 32px rgba(255,140,0,0.3)'
              }}
            >
              Launch App
            </Link>
            <a
              href="https://discord.gg/dKSdVdGWF"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 px-8 py-4 text-sm font-semibold text-zinc-300 transition-colors hover:border-zinc-500 hover:text-white"
            >
              <Bot className="h-4 w-4" />
              Join Discord
            </a>
          </div>
        </div>

        {/* Scroll hint */}
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 animate-bounce text-zinc-600">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10 14l-6-6h12l-6 6z" />
          </svg>
        </div>
      </section>

      {/* ── Alpha — 3-way grid ─────────────────────────────────────────── */}
      <section className="px-4 py-24">
        <div className="mx-auto max-w-6xl">
          <p className="mb-3 text-center font-display text-xs font-semibold uppercase tracking-[0.2em] text-[#FF8C00]">
            Alpha
          </p>
          <h2 className="mb-14 text-center font-display text-3xl font-bold text-white md:text-4xl">
            Everything you need, nothing you don&apos;t.
          </h2>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {alphaCards.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="group rounded-[12px] border border-[#1A1A1A] bg-[#0A0A0A] p-6 transition-all duration-300"
                style={{ outline: '1px solid transparent' }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLElement
                  el.style.borderColor = 'rgba(255,140,0,0.35)'
                  el.style.boxShadow = '0 0 0 1px rgba(255,140,0,0.1), 0 8px 32px rgba(255,140,0,0.08)'
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLElement
                  el.style.borderColor = '#1A1A1A'
                  el.style.boxShadow = 'none'
                }}
              >
                <div
                  className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[#FF8C00]/25 bg-[#FF8C00]/10"
                >
                  <Icon className="h-5 w-5 text-[#FF8C00]" />
                </div>
                <h3 className="mb-2 font-display text-base font-semibold text-white">{title}</h3>
                <p className="text-sm leading-relaxed text-zinc-500">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Ecosystem — 2-way grid ────────────────────────────────── */}
      <section className="px-4 py-24">
        <div className="mx-auto max-w-6xl">
          <p className="mb-3 text-center font-display text-xs font-semibold uppercase tracking-[0.2em] text-[#FF8C00]">
            The Ecosystem
          </p>
          <h2 className="mb-14 text-center font-display text-3xl font-bold text-white md:text-4xl">
            Signals wherever you work.
          </h2>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Left — Discord Bot */}
            <div className="rounded-[12px] border border-[#1A1A1A] bg-[#0A0A0A] p-8">
              <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[#FF8C00]/25 bg-[#FF8C00]/10">
                <Bot className="h-5 w-5 text-[#FF8C00]" />
              </div>
              <h3 className="mb-3 font-display text-xl font-semibold text-white">
                Discord Bot Integration
              </h3>
              <p className="mb-6 text-sm leading-relaxed text-zinc-400">
                Bring the radar directly into your server. Our Discord bot streams real-time token
                alerts, whale movements, and custom watchlist pings — so your community never misses
                a move.
              </p>
              <ul className="space-y-3 text-sm text-zinc-500">
                {[
                  'Per-channel alert routing',
                  'Slash command token lookup',
                  'Configurable whale threshold',
                  'No-code setup in under 2 minutes',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#FF8C00]" />
                    {item}
                  </li>
                ))}
              </ul>
              <div className="mt-8">
                <a
                  href="https://discord.gg/dKSdVdGWF"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl border border-[#FF8C00]/40 bg-[#FF8C00]/10 px-5 py-2.5 text-sm font-semibold text-[#FF8C00] transition-colors hover:border-[#FF8C00]/70 hover:bg-[#FF8C00]/15"
                >
                  <Bot className="h-4 w-4" />
                  Add to Discord
                </a>
              </div>
            </div>

            {/* Right — Webhook alert code block */}
            <div className="rounded-[12px] border border-[#1A1A1A] bg-[#0A0A0A] p-8">
              <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[#FF8C00]/25 bg-[#FF8C00]/10">
                <Webhook className="h-5 w-5 text-[#FF8C00]" />
              </div>
              <h3 className="mb-3 font-display text-xl font-semibold text-white">
                Webhook Alerts
              </h3>
              <p className="mb-6 text-sm leading-relaxed text-zinc-400">
                Point any webhook URL at your own infrastructure. Get structured JSON payloads the
                moment your alert conditions are met — pipe them into Slack, Telegram, or your own
                trading bot.
              </p>

              {/* Code block */}
              <div className="overflow-hidden rounded-[12px] border border-[#1E1E1E] bg-[#070707]">
                {/* Tab bar */}
                <div className="flex items-center gap-1.5 border-b border-[#1E1E1E] px-4 py-2.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#FF5F57]" />
                  <span className="h-2.5 w-2.5 rounded-full bg-[#FFBD2E]" />
                  <span className="h-2.5 w-2.5 rounded-full bg-[#28C840]" />
                  <span className="ml-3 font-mono text-[10px] text-zinc-600">
                    webhook_payload.json
                  </span>
                </div>
                <pre className="overflow-x-auto px-5 py-4 font-mono text-xs leading-6">
                  {webhookSample.split('\n').map((line, i) => {
                    const keyMatch = line.match(/^(\s*)"([^"]+)"(:\s*)(.*)$/)
                    if (keyMatch) {
                      const [, indent, key, colon, value] = keyMatch
                      return (
                        <div key={i}>
                          <span className="text-zinc-600">{indent}</span>
                          <span className="text-[#FF8C00]/80">&quot;{key}&quot;</span>
                          <span className="text-zinc-500">{colon}</span>
                          <span className="text-emerald-400">{value.replace(/,$/, '')}</span>
                          {value.endsWith(',') && <span className="text-zinc-500">,</span>}
                        </div>
                      )
                    }
                    return (
                      <div key={i} className="text-zinc-600">
                        {line}
                      </div>
                    )
                  })}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer CTA ─────────────────────────────────────────────────── */}
      <section className="px-4 py-24 text-center">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-4 font-display text-3xl font-bold text-white md:text-4xl">
            Ready to trade smarter?
          </h2>
          <p className="mb-8 text-zinc-400">
            Access the full radar, whale tracker, and custom alerts — free to start.
          </p>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="rounded-[12px] border border-[#1A1A1A] bg-[#0A0A0A] p-8 text-left">
              <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[#FF8C00]/25 bg-[#FF8C00]/10">
                <Bookmark className="h-5 w-5 text-[#FF8C00]" />
              </div>
              <h3 className="mb-3 font-display text-xl font-semibold text-white">Use Hosted App</h3>
              <p className="mb-6 text-sm leading-relaxed text-zinc-400">
                Jump straight into Birdeye Radar to monitor tokens, whale moves, and live alert flows in seconds.
              </p>
              <Link
                to="/radar"
                className="inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold text-black transition-all duration-200"
                style={{
                  background: '#FF8C00',
                  boxShadow: '0 0 0 1px rgba(255,140,0,0.4), 0 0 32px rgba(255,140,0,0.25)',
                }}
              >
                <Bookmark className="h-4 w-4" />
                Open the Terminal
              </Link>
            </div>

            <div className="rounded-[12px] border border-[#1A1A1A] bg-[#0A0A0A] p-8 text-left">
              <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[#FF8C00]/25 bg-[#FF8C00]/10">
                <Github className="h-5 w-5 text-[#FF8C00]" />
              </div>
              <h3 className="mb-3 font-display text-xl font-semibold text-white">Self-Host From Source</h3>
              <p className="mb-6 text-sm leading-relaxed text-zinc-400">
                Run your own instance locally with your own API token and infrastructure. Full control, open-source flexibility.
              </p>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-[#FF8C00]/40 bg-[#FF8C00]/10 px-6 py-3 text-sm font-semibold text-[#FF8C00] transition-colors hover:border-[#FF8C00]/70 hover:bg-[#FF8C00]/15"
              >
                <Github className="h-4 w-4" />
                View on GitHub
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Minimal footer ─────────────────────────────────────────────── */}
      <footer className="border-t border-[#1A1A1A] px-4 py-8 text-center font-mono text-xs text-zinc-700">
        © {new Date().getFullYear()} Birdeye Radar · Built on Solana · Using Birdeye API 
      </footer>
    </div>
  )
}

export default LandingView
