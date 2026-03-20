import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nova v2 | Fuelled Energy Marketing",
  description: "Industrial equipment valuation intelligence platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-body text-on-surface min-h-full overflow-x-hidden selection:bg-primary/30 selection:text-white">
        {children}
      </body>
    </html>
  );
}
