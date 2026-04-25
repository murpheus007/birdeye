import { motion } from 'framer-motion'

interface LoadingPulseProps {
  message?: string
}

export const LoadingPulse = ({ message = 'Loading trending tokens' }: LoadingPulseProps) => {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-8">
      <div className="relative h-14 w-28 overflow-hidden rounded-full border border-neonOrange/45 bg-black/35 shadow-neon">
        <motion.div
          className="absolute inset-0 rounded-full border border-neonOrange/20 bg-gradient-to-br from-neonOrange/10 via-transparent to-neonSoft/10"
          animate={{ opacity: [0.75, 1, 0.75] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-neonOrange shadow-neon"
          animate={{ scale: [1, 0.85, 1], x: [-6, 6, -6] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute inset-y-1 left-4 right-4 rounded-full border border-neonOrange/40 bg-black/70"
          animate={{ x: [-42, 42, -42], scaleY: [1, 0.18, 1] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      <motion.p
        className="font-mono text-sm text-zinc-400"
        animate={{ opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        {message}
      </motion.p>
    </div>
  )
}

export default LoadingPulse
