function normalizeBaseUrl(input: string): string {
  return input.trim().replace(/\/+$/, '');
}

function getApiBaseUrl(): string {
  const configured = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL || '');
  if (configured) return configured;
  return '';
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
