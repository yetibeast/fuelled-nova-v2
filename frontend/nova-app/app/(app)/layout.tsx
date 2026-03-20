"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { SettingsDrawer } from "@/components/settings-drawer";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      if (localStorage.getItem("nova_authenticated") !== "true") {
        router.replace("/login");
        return;
      }
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;

  return (
    <>
      <Sidebar onSettingsClick={() => setSettingsOpen(true)} />
      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <main className="ml-[220px] min-h-screen p-7 max-md:ml-12 max-md:p-4 transition-[margin] duration-200">
        {children}
      </main>
    </>
  );
}
