import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["animejs"],
  async redirects() {
    return [
      {
        source: "/cases",
        destination: "/verdicts",
        permanent: true,
      },
      {
        source: "/cases/:slug*",
        destination: "/verdicts/:slug*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
