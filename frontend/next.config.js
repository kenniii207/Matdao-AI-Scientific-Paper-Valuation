/** @type {import('next').NextConfig} */
const nextConfig = {
  // Rewrites allowed for local dev to standalone backend. 
  // On Vercel, the /api directory is automatically handled by Serverless Functions.
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NODE_ENV === 'development' 
          ? 'http://localhost:8000/api/:path*' 
          : '/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
