"use client";

import { DataTable } from "@/components/ui/data-table";
import { StatusDot } from "@/components/ui/status-dot";

const HEALTH_DATA = [
  { name: "RCN Price References", rows: 116, freshness: "Current" },
  { name: "Market Value References", rows: 349, freshness: "Current" },
  { name: "Depreciation Obs.", rows: 266, freshness: "Current" },
  { name: "Evidence Intake", rows: 772, freshness: "Current" },
  { name: "Equipment Identities", rows: 151, freshness: "Current" },
  { name: "Escalation Factors", rows: 65, freshness: "Current" },
];

export function DataHealth() {
  const now = new Date().toISOString();

  return (
    <DataTable
      title="Data Health"
      badge="GOLD TABLES"
      headers={["DATA SOURCE", "ROWS", "FRESHNESS", "STATUS"]}
      headerAligns={["left", "right", "left", "left"]}
    >
      {HEALTH_DATA.map((d, i) => (
        <tr key={i} className="hover:bg-white/[0.04] transition-colors">
          <td className="px-6 py-3 text-on-surface font-medium">{d.name}</td>
          <td className="px-6 py-3 text-right text-secondary font-bold">{d.rows.toLocaleString()}</td>
          <td className="px-6 py-3 text-on-surface/50">{d.freshness}</td>
          <td className="px-6 py-3"><StatusDot date={now} /></td>
        </tr>
      ))}
    </DataTable>
  );
}
