import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "draw-bitch — рисуй и угадывай",
  description: "Совместная игра с друзьями: рисуй слово, угадывай в чате.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
