import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/backend', () => ({
  resolveBackendBaseUrl: vi.fn(),
}));

import { resolveBackendBaseUrl } from '@/lib/backend';
import { POST } from '@/app/api/upload/route';

const mockResolveBackendBaseUrl = vi.mocked(resolveBackendBaseUrl);

describe('POST /api/upload proxy', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  function makeUploadRequest(): Request {
    const form = new FormData();
    form.append('file', new Blob(['%PDF-1.4'], { type: 'application/pdf' }), 'paper.pdf');
    return new Request('http://localhost/api/upload', { method: 'POST', body: form });
  }

  it('returns 503 when backend is not configured in preview', async () => {
    mockResolveBackendBaseUrl.mockReturnValue(null);

    const response = await POST(makeUploadRequest());
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body.error).toContain('Preview backend not configured');
  });

  it('proxies backend response payload and status', async () => {
    mockResolveBackendBaseUrl.mockReturnValue('https://backend.local');
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 201,
        headers: { 'content-type': 'application/json; charset=utf-8' },
      }),
    );

    const response = await POST(makeUploadRequest());
    const body = await response.json();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe('https://backend.local/api/upload');
    expect(response.status).toBe(201);
    expect(body.ok).toBe(true);
    expect(response.headers.get('cache-control')).toBe('no-store');
  });

  it('returns 502 when backend cannot be reached', async () => {
    mockResolveBackendBaseUrl.mockReturnValue('https://backend.local');
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockRejectedValue(new Error('network down'));

    const response = await POST(makeUploadRequest());
    const body = await response.json();

    expect(response.status).toBe(502);
    expect(body.error).toBe('Unable to reach backend upload service.');
  });
});
