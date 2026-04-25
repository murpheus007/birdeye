import { Wallet } from 'lucide-react'
import { useWallet } from '@solana/wallet-adapter-react'
import { useWalletModal } from '@solana/wallet-adapter-react-ui'

type ConnectWalletButtonProps = {
  className?: string
  iconOnly?: boolean
}

const ConnectWalletButton = ({ className = '', iconOnly = false }: ConnectWalletButtonProps) => {
  const { connected } = useWallet()
  const { setVisible } = useWalletModal()

  if (connected) {
    return null
  }

  return (
    <button
      onClick={() => setVisible(true)}
      className={
        iconOnly
          ? `flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-neonOrange/45 bg-neonOrange/15 text-neonOrange transition hover:border-neonOrange/70 hover:bg-neonOrange/20 ${className}`
          : `flex h-11 items-center gap-2 rounded-xl border border-neonOrange/45 bg-neonOrange/15 px-3 text-sm font-medium text-neonOrange transition hover:border-neonOrange/70 hover:bg-neonOrange/20 ${className}`
      }
      title={iconOnly ? 'Connect Wallet' : undefined}
    >
      <Wallet className="h-4 w-4" />
      {!iconOnly && 'Connect Wallet'}
    </button>
  )
}

export default ConnectWalletButton