const DEFAULT_PROD_API_URL = 'https://matdao-backend.onrender.com';

function normalizeBaseUrl(input: string): string {
  return input.trim().replace(/\/+$/, '');
}

export function getApiBaseUrl(): string {
  const configured = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL || '');
  if (configured) return configured;

  if (typeof window !== 'undefined') {
    const host = window.location.hostname.toLowerCase();
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://localhost:8000';
    }
    if (host.includes('matdao-backend.onrender.com')) {
      return '';
    }
  }

  return DEFAULT_PROD_API_URL;
}

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath}`;
}

export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = 20000,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}
