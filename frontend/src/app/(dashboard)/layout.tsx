/**
 * Authenticated dashboard layout.
 * Provides a responsive sidebar (desktop: fixed, mobile: sheet overlay),
 * a topbar with user info, and a scrollable main content area.
 * Integrates AuthGuard for client-side role checking.
 * Passes the user role to the sidebar so only permitted nav items are shown.
 */
"use client";

import { useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Toaster } from "sonner";
import { SidebarNav, SidebarLogo } from "@/components/layout/sidebar-nav";
import { Topbar } from "@/components/layout/topbar";
import { AuthGuard } from "@/components/auth-guard";
import { ErrorBoundary } from "@/components/error-boundary";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/stores/auth-store";

interface DashboardLayoutProps {
  children: ReactNode;
}

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "\u05D3\u05D0\u05E9\u05D1\u05D5\u05E8\u05D3",
  "/management": "\u05DC\u05D5\u05D7 \u05D4\u05E0\u05D4\u05DC\u05D4",
  "/explorer": "\u05E1\u05D9\u05D9\u05E8 \u05DE\u05DB\u05E8\u05D6\u05D9\u05DD",
  "/analytics": "\u05E0\u05D9\u05EA\u05D5\u05D7 \u05E9\u05D5\u05E7",
  "/watchlist": "\u05E8\u05E9\u05D9\u05DE\u05EA \u05DE\u05E2\u05E7\u05D1",
};

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const email = useAuthStore((s) => s.email);
  const role = useAuthStore((s) => s.role);
  const pathname = usePathname();
  const pageTitle = PAGE_TITLES[pathname] ?? "";

  return (
    <AuthGuard>
      <Toaster position="top-right" dir="rtl" richColors />
      <div className="flex h-screen overflow-hidden">
        {/* ---- Desktop sidebar (hidden on mobile) ---- */}
        <aside className="hidden w-64 shrink-0 flex-col border-s border-sidebar-border bg-megido-sidebar-bg md:flex">
          <SidebarLogo />
          <Separator className="bg-sidebar-border" />
          <div className="mt-4 flex-1 overflow-y-auto">
            <SidebarNav role={role} />
          </div>
        </aside>

        {/* ---- Mobile sidebar (sheet overlay) ---- */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetContent
            side="right"
            className="w-64 border-l-0 bg-megido-sidebar-bg p-0"
          >
            <SidebarLogo />
            <Separator className="bg-sidebar-border" />
            <div className="mt-4 flex-1 overflow-y-auto">
              <SidebarNav role={role} onNavClick={() => setMobileOpen(false)} />
            </div>
          </SheetContent>
        </Sheet>

        {/* ---- Main content ---- */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar
            userEmail={email ?? ""}
            onMenuClick={() => setMobileOpen(true)}
            pageTitle={pageTitle}
          />
          <main className="flex-1 overflow-y-auto bg-megido-bg-main p-4 md:p-6">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
