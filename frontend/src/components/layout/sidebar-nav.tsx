/**
 * Sidebar navigation component.
 * Renders the navigation links with icons for the dashboard layout.
 * Used in both the desktop sidebar and the mobile sheet overlay.
 * Filters visible items based on the user's role.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  BarChart3,
  Compass,
  TrendingUp,
  Building2,
} from "lucide-react";
import type { UserRole } from "@/stores/auth-store";

// ---------------------------------------------------------------------------
// Nav item definitions
// ---------------------------------------------------------------------------

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  /** Which roles can see this nav item. "team" sees everything. */
  requiredRole: "team" | "all";
}

const navItems: NavItem[] = [
  { href: "/management", label: "לוח הנהלה", icon: LayoutDashboard, requiredRole: "all" },
  { href: "/dashboard", label: "דאשבורד", icon: BarChart3, requiredRole: "team" },
  { href: "/explorer", label: "סייר מכרזים", icon: Compass, requiredRole: "team" },
  { href: "/analytics", label: "ניתוח שוק", icon: TrendingUp, requiredRole: "team" },
];

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

interface SidebarNavProps {
  role?: UserRole;
  onNavClick?: () => void;
}

export function SidebarNav({ role, onNavClick }: SidebarNavProps) {
  const pathname = usePathname();

  // Filter items based on role
  const visibleItems = navItems.filter((item) => {
    if (item.requiredRole === "all") return true;
    return role === "team";
  });

  return (
    <nav className="flex flex-col gap-1 px-3">
      {visibleItems.map((item) => {
        const isActive = pathname === item.href;
        const Icon = item.icon;

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavClick}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-sidebar-accent text-white"
                : "text-megido-text-on-dark/70 hover:bg-sidebar-accent/50 hover:text-megido-text-on-dark",
            )}
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function SidebarLogo() {
  return (
    <div className="flex items-center gap-3 px-6 py-5">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-megido-primary">
        <Building2 className="h-5 w-5 text-white" />
      </div>
      <div>
        <h1 className="text-lg font-bold text-white">MEGIDO</h1>
        <p className="text-xs text-megido-text-on-dark/60">מכרזי קרקע</p>
      </div>
    </div>
  );
}
