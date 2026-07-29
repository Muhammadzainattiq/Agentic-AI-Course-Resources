import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root to this app so Next doesn't guess when multiple
  // lockfiles exist higher up the tree.
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
