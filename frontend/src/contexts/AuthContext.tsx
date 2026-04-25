import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react'
import bs58 from 'bs58'
import { useWallet } from '@solana/wallet-adapter-react'
import { terminalApi } from '../services/terminalApi'
import { AuthUser } from '../types/types'

type AuthContextValue = {
  user: AuthUser | null
  isAuthenticated: boolean
  isAuthenticating: boolean
  error: string | null
  authenticate: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export const AuthProvider = ({ children }: PropsWithChildren) => {
  const { publicKey, connected, signMessage, disconnect } = useWallet()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshMe = async () => {
    try {
      const payload = await terminalApi.getAuthMe()
      if (payload.authenticated && payload.user) {
        setUser(payload.user)
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
    }
  }

  useEffect(() => {
    void refreshMe()
  }, [])

  useEffect(() => {
    const walletAddress = publicKey?.toBase58()
    if (!connected || !walletAddress || !user) {
      return
    }

    if (user.wallet_address !== walletAddress) {
      setUser(null)
    }
  }, [connected, publicKey, user])

  const authenticate = async () => {
    if (!connected || !publicKey) {
      setError('Connect a wallet first')
      return
    }

    if (!signMessage) {
      setError('Selected wallet does not support message signing')
      return
    }

    setError(null)
    setIsAuthenticating(true)

    try {
      const walletAddress = publicKey.toBase58()
      const challenge = await terminalApi.getAuthChallenge(walletAddress)
      const signatureBytes = await signMessage(new TextEncoder().encode(challenge.message))
      const signature = bs58.encode(signatureBytes)
      const payload = await terminalApi.loginWithWallet(walletAddress, challenge.message, signature)

      if (!payload.authenticated || !payload.user) {
        throw new Error('Authentication failed')
      }

      setUser(payload.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
      throw err
    } finally {
      setIsAuthenticating(false)
    }
  }

  const logout = async () => {
    setError(null)
    await terminalApi.logout()
    setUser(null)
    if (connected) {
      await disconnect()
    }
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isAuthenticating,
      error,
      authenticate,
      logout,
    }),
    [user, isAuthenticating, error],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
