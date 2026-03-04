/**
 * Top bar component for the dashboard layout.
 * Shows a mobile menu trigger (hamburger), the current user email, and logout.
 * Uses the Zustand auth store for logout (clears cookie + state).
 */
"use client";

import { Menu, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/stores/auth-store";

interface TopbarProps {
  userEmail: string;
  onMenuClick: () => void;
}

export function Topbar({ userEmail, onMenuClick }: TopbarProps) {
  const logout = useAuthStore((s) => s.logout);

  function handleLogout() {
    logout();
    window.location.href = "/login";
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b border-megido-border bg-megido-bg-card px-4 md:px-6">
      {/* Mobile menu button -- hidden on desktop */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={onMenuClick}
        aria-label="פתח תפריט"
      >
        <Menu className="h-5 w-5" />
      </Button>

      <Separator orientation="vertical" className="h-6 md:hidden" />

      {/* Spacer */}
      <div className="flex-1" />

      {/* User info + logout */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-megido-text-muted" dir="ltr">
          {userEmail}
        </span>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleLogout}
          aria-label="יציאה"
          className="text-megido-text-muted hover:text-megido-danger"
        >
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
