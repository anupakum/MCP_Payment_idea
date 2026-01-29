/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: []
  },
  env: {
    FAST_MCP_API_URL: process.env.FAST_MCP_API_URL || 'http://localhost:8000',
  },
  // Allow cross-origin requests from custom domain (dynamically set from environment)
  allowedDevOrigins: process.env.DOMAIN_NAME ? [process.env.DOMAIN_NAME] : [],
  typescript: {
    // !! WARN !!
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors.
    // ignoreBuildErrors: false,
  },
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    // ignoreDuringBuilds: false,
  },
  // Enable strict mode for better development experience
  reactStrictMode: true,
  // Optimize images
  images: {
    domains: [],
    formats: ['image/webp']
  }
}

module.exports = nextConfig