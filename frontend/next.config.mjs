/** @type {import('next').NextConfig} */
const API_PROXY = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";

const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  async rewrites() {
    // Browser calls same-origin /api/* and /health → FastAPI backend
    return [
      { source: "/health", destination: `${API_PROXY}/health` },
      { source: "/api/:path*", destination: `${API_PROXY}/api/:path*` },
    ];
  },
};

export default nextConfig;
