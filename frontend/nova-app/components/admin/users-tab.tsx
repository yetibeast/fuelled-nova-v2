"use client";

import { useEffect, useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { fetchUsers, createUser, updateUser, deleteUser } from "@/lib/api";
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
  const [editId, setEditId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ name: "", email: "", password: "" });

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
      setError(e instanceof Error ? e.message : "Failed to update");
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete user "${name}"? This cannot be undone.`)) return;
    try {
      await deleteUser(id);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  }

  function startEdit(u: User) {
    setEditId(u.id);
    setEditForm({ name: u.name, email: u.email, password: "" });
  }

  async function handleSaveEdit(id: string) {
    setError(null);
    try {
      const updates: Record<string, string> = {};
      const orig = users.find((u) => u.id === id);
      if (editForm.name && editForm.name !== orig?.name) updates.name = editForm.name;
      if (editForm.email && editForm.email !== orig?.email) updates.email = editForm.email;
      if (editForm.password) updates.password = editForm.password;
      if (Object.keys(updates).length === 0) {
        setEditId(null);
        return;
      }
      await updateUser(id, updates);
      setEditId(null);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update");
    }
  }

  async function handleToggleStatus(id: string, currentStatus: string) {
    const newStatus = currentStatus === "active" ? "inactive" : "active";
    try {
      await updateUser(id, { status: newStatus });
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update status");
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

      <div className="glass-card rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.06] flex justify-between items-center">
          <h3 className="font-headline font-bold text-sm tracking-tight">Users</h3>
          <span className="text-[10px] font-mono text-secondary">{users.length} USERS</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead className="text-on-surface/30 border-b border-white/[0.05]">
              <tr>
                <th className="px-6 py-3 font-medium">NAME</th>
                <th className="px-6 py-3 font-medium">EMAIL</th>
                <th className="px-6 py-3 font-medium">ROLE</th>
                <th className="px-6 py-3 font-medium">STATUS</th>
                <th className="px-6 py-3 font-medium">LAST LOGIN</th>
                <th className="px-6 py-3 font-medium">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {users.map((u) => {
                const isEditing = editId === u.id;
                return (
                  <tr key={u.id} className="hover:bg-white/[0.04] transition-colors">
                    <td className="px-6 py-3 text-on-surface font-medium">
                      {isEditing ? (
                        <input
                          value={editForm.name}
                          onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                          className="bg-surface-container-lowest rounded px-2 py-1 text-xs text-on-surface w-full"
                        />
                      ) : (
                        u.name
                      )}
                    </td>
                    <td className="px-6 py-3 text-on-surface/50">
                      {isEditing ? (
                        <input
                          value={editForm.email}
                          onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                          className="bg-surface-container-lowest rounded px-2 py-1 text-xs text-on-surface w-full"
                        />
                      ) : (
                        u.email
                      )}
                    </td>
                    <td className="px-6 py-3">
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className="bg-transparent text-[10px] font-mono font-bold text-primary outline-none cursor-pointer"
                      >
                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                    <td className="px-6 py-3">
                      <button onClick={() => handleToggleStatus(u.id, u.status || "active")}>
                        {statusPill(u.status || "active")}
                      </button>
                    </td>
                    <td className="px-6 py-3 text-on-surface/50">
                      {u.last_login_at ? timeAgo(u.last_login_at) : "Never"}
                    </td>
                    <td className="px-6 py-3">
                      {isEditing ? (
                        <div className="flex items-center gap-2">
                          <input
                            placeholder="New password"
                            type="password"
                            value={editForm.password}
                            onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                            className="bg-surface-container-lowest rounded px-2 py-1 text-xs text-on-surface w-24"
                          />
                          <button onClick={() => handleSaveEdit(u.id)} className="text-emerald-400 hover:text-emerald-300">
                            <MaterialIcon icon="check" className="text-[16px]" />
                          </button>
                          <button onClick={() => setEditId(null)} className="text-on-surface/40 hover:text-on-surface/70">
                            <MaterialIcon icon="close" className="text-[16px]" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <button onClick={() => startEdit(u)} className="text-on-surface/30 hover:text-primary" title="Edit user">
                            <MaterialIcon icon="edit" className="text-[16px]" />
                          </button>
                          <button onClick={() => handleDelete(u.id, u.name)} className="text-on-surface/30 hover:text-red-400" title="Delete user">
                            <MaterialIcon icon="delete" className="text-[16px]" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
