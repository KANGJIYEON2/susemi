import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker 컨테이너 빌드용 — .next/standalone 으로 self-contained 출력
  output: "standalone",
};

export default nextConfig;
