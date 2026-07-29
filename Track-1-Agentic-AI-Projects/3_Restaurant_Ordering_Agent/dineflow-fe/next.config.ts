import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root; a stray lockfile in a parent dir otherwise wins.
  turbopack: { root: __dirname },
};

export default nextConfig;
