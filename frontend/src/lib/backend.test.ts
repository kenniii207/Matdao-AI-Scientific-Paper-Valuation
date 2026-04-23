import { afterEach, describe, expect, it } from 'vitest';

import { resolveBackendBaseUrl } from '@/lib/backend';

const ENV_KEYS = [
  'BACKEND_API_URL',
  'VERCEL_ENV',
  'BACKEND_API_URL_PREVIEW',
  'BACKEND_API_URL_PRODUCTION',
  'BACKEND_API_URL_DEVELOPMENT',
] as const;

describe('resolveBackendBaseUrl', () => {
  afterEach(() => {
    for (const key of ENV_KEYS) {
      delete process.env[key];
    }
  });

  it('prefers direct override when configured', () => {
    process.env.BACKEND_API_URL = 'https://example.com/';
    process.env.VERCEL_ENV = 'preview';
    process.env.BACKEND_API_URL_PREVIEW = 'https://preview.example.com';

    expect(resolveBackendBaseUrl()).toBe('https://example.com');
  });

  it('returns null for preview when preview backend is missing', () => {
    process.env.VERCEL_ENV = 'preview';

    expect(resolveBackendBaseUrl()).toBeNull();
  });

  it('uses production default when production env is set', () => {
    process.env.VERCEL_ENV = 'production';

    expect(resolveBackendBaseUrl()).toBe('https://matdao-backend.onrender.com');
  });

  it('uses development default outside vercel production/preview', () => {
    expect(resolveBackendBaseUrl()).toBe('http://localhost:8000');
  });
});
