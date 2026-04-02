"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { SettingsDrawer } from "@/components/settings-drawer";
import { verifyAuth, type NovaUser } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<NovaUser | null>(null);
  const [ready, setReady] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth < 768) {
      setSidebarCollapsed(true);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    verifyAuth().then((u) => {
      if (!u) {
        router.replace("/login");
        return;
      }
      setUser(u);
      setReady(true);
    });
  }, [router]);

  if (!ready) return null;

  return (
    <>
      <Sidebar onSettingsClick={() => setSettingsOpen(true)} userRole={user?.role} collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />
      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <main className={`${sidebarCollapsed ? "ml-[48px]" : "ml-[220px]"} min-h-screen p-7 max-md:ml-12 max-md:p-4 transition-[margin] duration-200`}>
        {children}
      </main>
    </>
  );
}
