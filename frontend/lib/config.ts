/**
 * Centralized API & WebSocket Configuration
 * In development, falls back to localhost:8000.
 * In production, reads NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WS_URL.
 */
export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

export const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ||
  (API_BASE.startsWith('https://')
    ? API_BASE.replace('https://', 'wss://')
    : API_BASE.replace('http://', 'ws://'));
