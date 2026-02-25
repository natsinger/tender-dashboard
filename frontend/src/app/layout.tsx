/**
 * Root layout for the MEGIDO Tender Intelligence Dashboard.
 * Sets RTL direction, Hebrew language, loads Inter + Heebo fonts,
 * and wraps the app in QueryClientProvider + TooltipProvider.
 */
import type { Metadata } from "next";
import { Inter, Heebo } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryProvider } from "@/providers/query-provider";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const heebo = Heebo({
  variable: "--font-heebo",
  subsets: ["hebrew", "latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "MEGIDO | מערכת מכרזי קרקע",
  description:
    "מערכת מודיעין למכרזי קרקע — ניתוח שוק, מעקב מכרזים, וניהול צוות",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="he" dir="rtl">
      <body
        className={`${inter.variable} ${heebo.variable} font-sans antialiased`}
      >
        <QueryProvider>
          <TooltipProvider delayDuration={300}>{children}</TooltipProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
