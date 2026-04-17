import { NextResponse } from 'next/server';
import { resolveBackendBaseUrl } from '@/lib/backend';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function previewBackendMissingResponse() {
  return NextResponse.json(
    {
      error:
        'Preview backend not configured. Set BACKEND_API_URL or BACKEND_API_URL_PREVIEW in Vercel Project Settings.',
    },
    { status: 503 },
  );
}

export async function POST(request: Request) {
  const backendBaseUrl = resolveBackendBaseUrl();
  if (!backendBaseUrl) return previewBackendMissingResponse();

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ error: 'Invalid upload payload.' }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${backendBaseUrl}/api/upload`, {
      method: 'POST',
      body: formData,
      cache: 'no-store',
    });

    const contentType = upstream.headers.get('content-type') || 'application/json; charset=utf-8';
    const body = await upstream.arrayBuffer();
    return new Response(body, {
      status: upstream.status,
      headers: {
        'content-type': contentType,
        'cache-control': 'no-store',
      },
    });
  } catch {
    return NextResponse.json({ error: 'Unable to reach backend upload service.' }, { status: 502 });
  }
}
