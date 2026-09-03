/** @type {import('next').NextConfig} */

const backendUrl = process.env.INTENTLOCK_BACKEND_URL?.replace(/\/$/, '')

const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },

  images: {
    unoptimized: true,
  },

  async rewrites() {
    if (!backendUrl) {
      return []
    }

    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig