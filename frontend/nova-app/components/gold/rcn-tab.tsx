"use client";

import { useEffect, useState } from "react";
import { FilterableTable, ColumnDef } from "@/components/ui/filterable-table";
import { MaterialIcon } from "@/components/ui/material-icon";
import { fetchGoldRcn, updateGoldRcn, deleteGoldRcn } from "@/lib/api";
import { formatPrice } from "@/lib/utils";

interface RcnRow {
  id: string;
  canonical_manufacturer: string;
  canonical_model: string;
  equipment_class: string | null;
  drive_type: string | null;
  stage_config: string | null;
  escalated_rcn_cad: number | null;
  confidence: number | null;
  validation_status: string | null;
  notes: string | null;
  effective_date: string | null;
}

export function RcnTab() {
  const [rows, setRows] = useState<RcnRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editId, setEditId] = useState<string | null>(null);
  const [editRcn, setEditRcn] = useState("");
  const [editStatus, setEditStatus] = useState("");

  useEffect(() => {
    fetchGoldRcn()
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, []);

  async function handleSave(id: string) {
    try {
      const rcn = parseFloat(editRcn);
      const updates: Record<string, unknown> = {
        validation_status: editStatus,
      };
      if (!Number.isNaN(rcn)) updates.escalated_rcn_cad = rcn;
      await updateGoldRcn(id, updates);
      setEditId(null);
      const fresh = await fetchGoldRcn();
      setRows(fresh);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this RCN reference? This cannot be undone.")) return;
    try {
      await deleteGoldRcn(id);
      setRows((prev) => prev.filter((r) => r.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  if (error) return <div className="text-red-400 font-mono text-sm p-4">Error: {error}</div>;

  const columns: ColumnDef<RcnRow>[] = [
    {
      key: "canonical_manufacturer",
      header: "MANUFACTURER",
      filter: "text",
      render: (r) => <span className="text-on-surface font-medium">{r.canonical_manufacturer}</span>,
    },
    {
      key: "canonical_model",
      header: "MODEL",
      filter: "text",
      render: (r) => <span className="text-on-surface/70">{r.canonical_model}</span>,
    },
    {
      key: "equipment_class",
      header: "CLASS",
      filter: "select",
      render: (r) => <span className="text-on-surface/50">{r.equipment_class || "---"}</span>,
    },
    {
      key: "drive_type",
      header: "DRIVE",
      filter: "select",
      render: (r) => <span className="text-on-surface/50">{r.drive_type || "---"}</span>,
    },
    {
      key: "escalated_rcn_cad",
      header: "RCN (CAD)",
      align: "right",
      filter: "none",
      render: (r) =>
        editId === r.id ? (
          <input
            className="w-24 bg-surface-container-lowest rounded px-2 py-1 text-xs text-right text-on-surface"
            defaultValue={r.escalated_rcn_cad ?? ""}
            onChange={(e) => setEditRcn(e.target.value)}
          />
        ) : (
          <span className="text-secondary font-bold">{formatPrice(r.escalated_rcn_cad)}</span>
        ),
    },
    {
      key: "confidence",
      header: "CONF",
      align: "right",
      filter: "none",
      render: (r) => (
        <span className="text-on-surface/50">
          {r.confidence != null ? (r.confidence * 100).toFixed(0) + "%" : "---"}
        </span>
      ),
    },
    {
      key: "validation_status",
      header: "STATUS",
      filter: "select",
      render: (r) =>
        editId === r.id ? (
          <select
            className="bg-surface-container-lowest rounded px-2 py-1 text-xs text-on-surface"
            defaultValue={r.validation_status || "pending"}
            onChange={(e) => setEditStatus(e.target.value)}
          >
            <option value="pending">pending</option>
            <option value="validated">validated</option>
            <option value="rejected">rejected</option>
          </select>
        ) : (
          <span
            className={`text-xs font-mono ${
              r.validation_status === "validated"
                ? "text-emerald-400"
                : r.validation_status === "rejected"
                  ? "text-red-400"
                  : "text-on-surface/40"
            }`}
          >
            {r.validation_status || "pending"}
          </span>
        ),
    },
  ];

  return (
    <FilterableTable<RcnRow>
      title="RCN Price References"
      badge={`${rows.length} REFS`}
      columns={columns}
      data={rows}
      rowKey={(r) => r.id}
      actions={(r) =>
        editId === r.id ? (
          <div className="flex gap-2">
            <button onClick={() => handleSave(r.id)} className="text-emerald-400 hover:text-emerald-300">
              <MaterialIcon icon="check" className="text-[16px]" />
            </button>
            <button onClick={() => setEditId(null)} className="text-on-surface/40 hover:text-on-surface/70">
              <MaterialIcon icon="close" className="text-[16px]" />
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => {
                setEditId(r.id);
                setEditRcn(r.escalated_rcn_cad != null ? String(r.escalated_rcn_cad) : "");
                setEditStatus(r.validation_status || "pending");
              }}
              className="text-on-surface/30 hover:text-primary"
            >
              <MaterialIcon icon="edit" className="text-[16px]" />
            </button>
            <button onClick={() => handleDelete(r.id)} className="text-on-surface/30 hover:text-red-400">
              <MaterialIcon icon="delete" className="text-[16px]" />
            </button>
          </div>
        )
      }
    />
  );
}
