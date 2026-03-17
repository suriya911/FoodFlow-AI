/** @type {import('next').NextConfig} */
const nextConfig = {
  // Leaflet does not support React 18 Strict Mode's double-mount behavior.
  // Disabling it prevents "Map container is already initialized" in dev.
  reactStrictMode: false,
  // standalone is only used when building inside Docker (set DOCKER_BUILD=1)
  ...(process.env.DOCKER_BUILD === '1' ? { output: 'standalone' } : {}),
}

module.exports = nextConfig
