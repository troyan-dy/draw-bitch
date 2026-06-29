/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Минимальный self-contained сервер: .next/standalone тащит только реально
  // используемые зависимости — лёгкий рантайм-образ для сервера.
  output: "standalone",
};

export default nextConfig;
