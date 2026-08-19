import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* This app lives in a monorepo. Without an explicit root, Turbopack walks up
     past the repository looking for a lockfile and warns about the one in the
     user's home directory. */
  turbopack: {
    root: path.join(__dirname, "..", ".."),
  },
};

export default nextConfig;
