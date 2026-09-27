import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  agentRules: false,
  devIndicators: false,
  experimental: { proxyClientMaxBodySize: "110mb" },
  async rewrites() {
    // Vercel Services routes /api to FastAPI before the Next.js service.
    if (process.env.VERCEL) return [];
    return [{ source: "/api/:path*", destination: `${process.env.MEMORY_ATLAS_API_URL ?? "http://127.0.0.1:8000"}/api/:path*` }];
  },
};

export default nextConfig;
