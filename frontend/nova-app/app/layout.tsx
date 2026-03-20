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
      <body className="font-body text-on-surface min-h-full overflow-x-hidden selection:bg-primary/30 selection:text-white">
        {children}
      </body>
    </html>
  );
}
