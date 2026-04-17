const DEFAULT_PROD_BACKEND_URL = 'https://matdao-backend.onrender.com';
const DEFAULT_DEV_BACKEND_URL = 'http://localhost:8000';

function normalizeBaseUrl(input: string | undefined): string {
  return (input || '').trim().replace(/\/+$/, '');
}

export function resolveBackendBaseUrl(): string | null {
  const direct = normalizeBaseUrl(process.env.BACKEND_API_URL);
  if (direct) return direct;

  const vercelEnv = process.env.VERCEL_ENV;
  if (vercelEnv === 'preview') {
    const previewUrl = normalizeBaseUrl(process.env.BACKEND_API_URL_PREVIEW);
    return previewUrl || null;
  }

  if (vercelEnv === 'production') {
    const productionUrl = normalizeBaseUrl(process.env.BACKEND_API_URL_PRODUCTION);
    return productionUrl || DEFAULT_PROD_BACKEND_URL;
  }

  const developmentUrl = normalizeBaseUrl(process.env.BACKEND_API_URL_DEVELOPMENT);
  return developmentUrl || DEFAULT_DEV_BACKEND_URL;
}
