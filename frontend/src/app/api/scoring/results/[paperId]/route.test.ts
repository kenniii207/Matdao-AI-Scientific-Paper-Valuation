import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/backend', () => ({
  resolveBackendBaseUrl: vi.fn(),
}));

import { resolveBackendBaseUrl } from '@/lib/backend';
import { GET } from '@/app/api/scoring/results/[paperId]/route';

const mockResolveBackendBaseUrl = vi.mocked(resolveBackendBaseUrl);

describe('GET /api/scoring/results/[paperId] proxy', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('returns 503 when backend is not configured in preview', async () => {
    mockResolveBackendBaseUrl.mockReturnValue(null);

    const response = await GET(new Request('http://localhost/api/scoring/results/abc'), {
      params: { paperId: 'abc' },
    });
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body.error).toContain('Preview backend not configured');
  });

  it('encodes paper id and proxies upstream response', async () => {
    mockResolveBackendBaseUrl.mockReturnValue('https://backend.local');
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ id: 'p 1', total_score: 88 }), {
        status: 200,
        headers: { 'content-type': 'application/json; charset=utf-8' },
      }),
    );

    const response = await GET(new Request('http://localhost/api/scoring/results/p%201'), {
      params: { paperId: 'p 1' },
    });
    const body = await response.json();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe('https://backend.local/api/scoring/results/p%201');
    expect(response.status).toBe(200);
    expect(body.total_score).toBe(88);
  });

  it('returns 502 when backend request fails', async () => {
    mockResolveBackendBaseUrl.mockReturnValue('https://backend.local');
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockRejectedValue(new Error('network down'));

    const response = await GET(new Request('http://localhost/api/scoring/results/abc'), {
      params: { paperId: 'abc' },
    });
    const body = await response.json();

    expect(response.status).toBe(502);
    expect(body.error).toBe('Unable to reach backend scoring service.');
  });
});
