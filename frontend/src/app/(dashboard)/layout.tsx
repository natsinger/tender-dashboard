/**
 * Authenticated dashboard layout.
 * Provides a responsive sidebar (desktop: fixed, mobile: sheet overlay),
 * a topbar with user info, and a scrollable main content area.
 * Integrates AuthGuard for client-side role checking.
 * Passes the user role to the sidebar so only permitted nav items are shown.
 */
"use client";

import { useState, useEffect, type ReactNode } from "react";
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

/** Read the user_email cookie value (client-side only). */
function getUserEmailFromCookie(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)user_email=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const role = useAuthStore((s) => s.role);

  useEffect(() => {
    setUserEmail(getUserEmailFromCookie());
  }, []);

  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        {/* ---- Desktop sidebar (hidden on mobile) ---- */}
        <aside className="hidden w-64 shrink-0 flex-col border-l border-sidebar-border bg-megido-sidebar-bg md:flex">
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
            userEmail={userEmail}
            onMenuClick={() => setMobileOpen(true)}
          />
          <main className="flex-1 overflow-y-auto bg-megido-bg-main p-4 md:p-6">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
