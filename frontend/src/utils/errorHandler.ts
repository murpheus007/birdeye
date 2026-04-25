/**
 * Error handler utility for API errors, particularly rate limiting.
 */

export type APIErrorResponse = {
  error?: string
  message?: string
  status?: number
}

/**
 * Check if an error is a rate limit/throttle error
 */
export const isRateLimitError = (error: unknown): boolean => {
  if (error instanceof Error) {
    const msg = error.message.toLowerCase()
    return msg.includes('data_throttled') || msg.includes('throttled') || msg.includes('cooling down')
  }
  if (typeof error === 'string') {
    return error.toLowerCase().includes('data_throttled') || error.toLowerCase().includes('cooling down')
  }
  return false
}

/**
 * Get a user-friendly message from an API error
 */
export const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    const msg = error.message
    
    // Check for specific rate limit messages
    if (msg.includes('DATA_THROTTLED') || msg.includes('cooling down')) {
      return '🌡️ Radar is cooling down to save energy. Try again in 60 seconds.'
    }
    if (msg.includes('429')) {
      return 'Too many requests. Please wait a moment before trying again.'
    }
    
    return msg
  }
  if (typeof error === 'string') {
    return error
  }
  return 'An unexpected error occurred'
}

/**
 * Determine the type of toast to show based on error
 */
export const getToastKind = (error: unknown): 'error' | 'info' => {
  if (isRateLimitError(error)) {
    return 'info' // Rate limit is informational, not a critical error
  }
  return 'error'
}
