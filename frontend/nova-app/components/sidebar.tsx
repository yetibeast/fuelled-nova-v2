"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { logout, fetchRecentPricing } from "@/lib/api";

const NAV_ITEMS: { section?: string; label?: string; icon?: string; href?: string; adminOnly?: boolean }[] = [
  { section: "INTELLIGENCE" },
  { label: "Dashboard", icon: "grid_view", href: "/" },
  { label: "Pricing Agent", icon: "chat", href: "/pricing" },
  { label: "Reports", icon: "description", href: "/reports" },
  { label: "Competitive", icon: "monitoring", href: "/competitive" },
  { label: "Methodology", icon: "science", href: "/methodology" },
  { section: "DATA" },
  { label: "Market Data", icon: "database", href: "/market" },
  { section: "OPERATIONS", adminOnly: true },
  { label: "Gold Tables", icon: "table_chart", href: "/gold-tables", adminOnly: true },
  { label: "Calibration", icon: "tune", href: "/calibration", adminOnly: true },
  { label: "Scrapers", icon: "cloud_sync", href: "/scrapers", adminOnly: true },
  { label: "AI Management", icon: "psychology", href: "/ai-management", adminOnly: true },
  { label: "Admin", icon: "admin_panel_settings", href: "/admin", adminOnly: true },
];

interface SidebarProps {
  onSettingsClick: () => void;
  userRole?: string;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

interface RecentItem {
  title: string;
  confidence: string;
  timestamp: string;
}

export function Sidebar({ onSettingsClick, userRole, collapsed, setCollapsed }: SidebarProps) {
  const isAdmin = userRole === "admin";
  const pathname = usePathname();
  const router = useRouter();
  const [activity, setActivity] = useState<RecentItem[]>([]);

  useEffect(() => {
    fetchRecentPricing().then(setActivity).catch(() => {});
  }, []);

  function isActive(href: string) {
    if (href === "/") return pathname === "/" || pathname === "";
    return pathname.startsWith(href);
  }

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <>
      {/* Mobile overlay */}
      {!collapsed && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setCollapsed(true)}
        />
      )}

      <aside
        className="fixed left-0 top-0 h-full frosted-panel z-50 flex flex-col transition-all duration-200 ease-in-out"
        style={{ width: collapsed ? 48 : 220 }}
      >
        {/* Logo */}
        <div className="px-5 py-5 flex items-center gap-3 border-b border-white/[0.06] shrink-0">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/20 shrink-0"
          >
            <span className="font-headline font-bold text-white text-sm">N</span>
          </button>
          {!collapsed && (
            <div className="overflow-hidden">
              <div className="font-headline font-bold text-sm text-on-surface tracking-tight">Fuelled<span className="text-primary">Nova</span></div>
              <div className="text-[9px] font-mono text-secondary tracking-widest">PRICING ENGINE</div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto">
          {NAV_ITEMS.map((item, i) => {
            if (item.adminOnly && !isAdmin) return null;
            if ("section" in item && item.section) {
              if (collapsed) return null;
              return (
                <div key={i} className="px-5 pt-5 pb-2 text-[9px] font-mono text-secondary/60 uppercase tracking-[0.2em]">
                  {item.section}
                </div>
              );
            }
            const active = isActive(item.href!);
            return (
              <button
                key={i}
                onClick={() => {
                  router.push(item.href!);
                  if (window.innerWidth < 768) setCollapsed(true);
                }}
                className={`w-full flex items-center gap-3 py-[11px] transition-all duration-150 text-[13px] font-medium ${
                  collapsed ? "px-3 justify-center" : "px-5"
                } ${
                  active
                    ? "border-l-[3px] border-l-primary bg-primary/[0.06] text-on-surface"
                    : "border-l-[3px] border-l-transparent text-on-surface/50 hover:bg-white/[0.04] hover:text-on-surface/80"
                }`}
              >
                <MaterialIcon
                  icon={item.icon!}
                  className={`text-[20px] ${active ? "text-primary" : ""}`}
                />
                {!collapsed && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Activity feed */}
        {!collapsed && activity.length > 0 && (
          <div className="px-5 py-3 border-t border-white/[0.06]">
            <div className="text-[9px] font-mono text-secondary/60 uppercase tracking-[0.2em] mb-2">Recent</div>
            {activity.map((a, i) => (
              <button
                key={i}
                onClick={() => { router.push("/pricing"); if (window.innerWidth < 768) setCollapsed(true); }}
                className="w-full text-left py-1.5 group"
              >
                <div className="text-[11px] text-on-surface/50 group-hover:text-on-surface/80 truncate transition-colors">
                  {a.title}
                </div>
                <div className="text-[9px] font-mono text-on-surface/20">{a.timestamp?.slice(0, 10)}</div>
              </button>
            ))}
          </div>
        )}

        {/* Settings button — admin only */}
        {isAdmin && (
          <button
            onClick={onSettingsClick}
            className={`flex items-center gap-3 py-3 border-t border-white/[0.06] transition-colors text-on-surface/50 hover:text-on-surface/80 hover:bg-white/[0.04] ${
              collapsed ? "px-3 justify-center" : "px-5"
            }`}
          >
            <MaterialIcon icon="settings" className="text-[20px]" />
            {!collapsed && <span className="text-[13px] font-medium">Settings</span>}
          </button>
        )}

        {/* Footer */}
        <div className={`px-5 py-4 border-t border-white/[0.06] flex items-center ${collapsed ? "justify-center" : "justify-between"}`}>
          {!collapsed && (
            <div className="text-[9px] font-mono text-on-surface/30 leading-relaxed min-w-0">
              Fuelled Energy Marketing Inc.
            </div>
          )}
          <button
            onClick={handleLogout}
            className="text-on-surface/30 hover:text-primary transition-colors shrink-0"
            title="Sign out"
          >
            <MaterialIcon icon="logout" className="text-[18px]" />
          </button>
        </div>
      </aside>
    </>
  );
}
