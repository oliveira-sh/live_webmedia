
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig = {
  output: "export",          // static export – serve with any HTTP server
  trailingSlash: true,
  basePath,
  images: { unoptimized: true },
};

export default nextConfig;
