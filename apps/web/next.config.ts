import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /*
   * Pin Turbopack's root to this app. Auto-detection walks up to the monorepo
   * root because of the workspace package.json, which produces chunk paths
   * above the directory the dev server serves.
   */
  turbopack: {
    root: __dirname,
  },

  /*
   * The dev server refuses asset requests from origins it does not recognise,
   * and it does not treat 127.0.0.1 as the same origin as localhost. Visiting
   * the app on 127.0.0.1 therefore gets 403 on its own JavaScript: the page
   * renders its server HTML and then never hydrates, so nothing is clickable
   * and no data ever loads. Allowing both spellings avoids that trap.
   */
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
