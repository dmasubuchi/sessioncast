import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",  // static HTML export for Firebase Hosting
  trailingSlash: true,
};

export default nextConfig;
