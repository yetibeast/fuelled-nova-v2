"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { fetchUsers, createUser, updateUser } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  last_login_at: string | null;
  created_at: string | null;
}

const ROLES = ["admin", "analyst", "viewer"];

export function UsersTab() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "analyst", password: "" });
  const [saving, setSaving] = useState(false);

  function load() {
    fetchUsers()
      .then((data: User[]) => setUsers(data))
      .catch((e: Error) => setError(e.message));
  }

  useEffect(load, []);

  async function handleCreate() {
    setSaving(true);
    setError(null);
    try {
      await createUser(form);
      setForm({ name: "", email: "", role: "analyst", password: "" });
      setShowForm(false);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  }

  async function handleRoleChange(id: string, role: string) {
    try {
      await updateUser(id, { role });
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update user");
    }
  }

  const statusPill = (status: string) => {
    const color = status === "active" ? "text-emerald-400 bg-emerald-500/10" : "text-red-400 bg-red-500/10";
    return <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${color}`}>{status}</span>;
  };

  return (
    <>
      {error && <div className="text-red-400 font-mono text-xs mb-4">Error: {error}</div>}

      <div className="flex justify-end mb-4">
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-primary/10 border border-primary/30 text-xs font-mono text-primary hover:bg-primary/20 transition-all"
        >
          {showForm ? "Cancel" : "Add User"}
        </button>
      </div>

      {showForm && (
        <div className="glass-card rounded-xl p-5 mb-6 grid grid-cols-2 gap-4">
          <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="recessed-input rounded-lg px-3 py-2 text-xs font-mono text-on-surface outline-none" />
          <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="recessed-input rounded-lg px-3 py-2 text-xs font-mono text-on-surface outline-none" />
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}
            className="recessed-input rounded-lg px-3 py-2 text-xs font-mono text-on-surface outline-none">
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <input placeholder="Password" type="password" value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="recessed-input rounded-lg px-3 py-2 text-xs font-mono text-on-surface outline-none" />
          <div className="col-span-2 flex justify-end">
            <button onClick={handleCreate} disabled={saving || !form.name || !form.email || !form.password}
              className="px-4 py-2 rounded-lg bg-primary text-white text-xs font-mono font-bold disabled:opacity-40 hover:bg-primary/90 transition-colors">
              {saving ? "Creating..." : "Create User"}
            </button>
          </div>
        </div>
      )}

      <DataTable
        title="Users"
        badge={`${users.length} USERS`}
        headers={["NAME", "EMAIL", "ROLE", "STATUS", "LAST LOGIN", "CREATED"]}
      >
        {users.map((u) => (
          <tr key={u.id} className="hover:bg-white/[0.04] transition-colors">
            <td className="px-6 py-3 text-on-surface font-medium">{u.name}</td>
            <td className="px-6 py-3 text-on-surface/50">{u.email}</td>
            <td className="px-6 py-3">
              <select
                value={u.role}
                onChange={(e) => handleRoleChange(u.id, e.target.value)}
                className="bg-transparent text-[10px] font-mono font-bold text-primary outline-none cursor-pointer"
              >
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </td>
            <td className="px-6 py-3">{statusPill(u.status || "active")}</td>
            <td className="px-6 py-3 text-on-surface/50">{u.last_login_at ? timeAgo(u.last_login_at) : "Never"}</td>
            <td className="px-6 py-3 text-on-surface/30">{u.created_at ? timeAgo(u.created_at) : "---"}</td>
          </tr>
        ))}
      </DataTable>
    </>
  );
}
