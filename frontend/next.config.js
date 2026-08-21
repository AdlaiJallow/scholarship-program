/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Small, optimized bundles and mobile-first delivery matter on the
  // low-bandwidth connections this portal has to work over (system
  // specification §17) — keep this config minimal rather than pulling in
  // bundle-inflating defaults.
};

module.exports = nextConfig;
