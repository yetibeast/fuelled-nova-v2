"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { StatusDot } from "@/components/ui/status-dot";
import { fetchGoldHealth } from "@/lib/api";

interface HealthRow {
  name: string;
  table: string;
  rows: number;
}

export function DataHealth() {
  const [data, setData] = useState<HealthRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGoldHealth()
      .then((rows: HealthRow[]) => {
        setData(rows);
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  const now = new Date().toISOString();

  if (error) {
    return (
      <div className="glass-card rounded-xl p-6 text-red-400 font-mono text-xs">
        Failed to load data health: {error}
      </div>
    );
  }

  return (
    <DataTable
      title="Data Health"
      badge="GOLD TABLES"
      headers={["DATA SOURCE", "ROWS", "FRESHNESS", "STATUS"]}
      headerAligns={["left", "right", "left", "left"]}
    >
      {loading ? (
        <tr>
          <td colSpan={4} className="px-6 py-6 text-center text-on-surface/40 font-mono text-xs">
            Loading gold table health...
          </td>
        </tr>
      ) : (
        data.map((d, i) => (
          <tr key={i} className="hover:bg-white/[0.04] transition-colors">
            <td className="px-6 py-3 text-on-surface font-medium">{d.name}</td>
            <td className="px-6 py-3 text-right text-secondary font-bold">{d.rows.toLocaleString()}</td>
            <td className="px-6 py-3 text-on-surface/50">Live</td>
            <td className="px-6 py-3"><StatusDot date={now} /></td>
          </tr>
        ))
      )}
    </DataTable>
  );
}
