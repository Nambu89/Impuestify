/**
 * Conditional logger for development environments.
 * In production, all logs are disabled.
 */

const isDev = import.meta.env.DEV;

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface Logger {
  debug: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
}

const noop = () => {};

/**
 * Development-only logger.
 * All methods are no-ops in production.
 */
export const logger: Logger = {
  debug: isDev ? (...args: unknown[]) => console.debug('[DEBUG]', ...args) : noop,
  info: isDev ? (...args: unknown[]) => console.info('[INFO]', ...args) : noop,
  warn: isDev ? (...args: unknown[]) => console.warn('[WARN]', ...args) : noop,
  error: isDev ? (...args: unknown[]) => console.error('[ERROR]', ...args) : noop,
};

export default logger;
