"use client";

import { useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { createScraper } from "@/lib/api";

const SCHEDULE_PRESETS = [
  { label: "Every 6h", value: "0 */6 * * *" },
  { label: "Every 12h", value: "0 */12 * * *" },
  { label: "Daily (midnight)", value: "0 0 * * *" },
  { label: "Daily (2 AM)", value: "0 2 * * *" },
  { label: "Manual", value: "" },
  { label: "Custom", value: "__custom__" },
];

const TYPE_OPTIONS = ["scrapekit", "standalone", "harvester"];

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function AddScraperModal({ open, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [scraperType, setScraperType] = useState("scrapekit");
  const [schedulePreset, setSchedulePreset] = useState("0 */6 * * *");
  const [customCron, setCustomCron] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const schedule = schedulePreset === "__custom__" ? customCron : schedulePreset;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError("Name is required"); return; }
    setSaving(true);
    setError(null);
    try {
      await createScraper({
        name: name.trim().toLowerCase().replace(/\s+/g, "_"),
        url: url.trim(),
        scraper_type: scraperType,
        schedule_cron: schedule || undefined,
      });
      setName("");
      setUrl("");
      setScraperType("scrapekit");
      setSchedulePreset("0 */6 * * *");
      setCustomCron("");
      onCreated();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create scraper");
    }
    setSaving(false);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="glass-card rounded-xl p-6 w-full max-w-md relative z-10">
        <div className="flex justify-between items-center mb-5">
          <h3 className="font-headline font-bold text-sm tracking-tight">Add Scraper Target</h3>
          <button onClick={onClose} className="text-on-surface/30 hover:text-on-surface/70">
            <MaterialIcon icon="close" className="text-[18px]" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-[10px] font-mono text-on-surface/40 uppercase tracking-widest mb-1 block">
              Name
            </label>
            <input
              className="recessed-input rounded-lg w-full px-3 py-2 text-xs text-on-surface font-mono"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. machinio"
            />
          </div>

          {/* URL */}
          <div>
            <label className="text-[10px] font-mono text-on-surface/40 uppercase tracking-widest mb-1 block">
              URL
            </label>
            <input
              className="recessed-input rounded-lg w-full px-3 py-2 text-xs text-on-surface font-mono"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
            />
          </div>

          {/* Type */}
          <div>
            <label className="text-[10px] font-mono text-on-surface/40 uppercase tracking-widest mb-1 block">
              Type
            </label>
            <select
              className="recessed-input rounded-lg w-full px-3 py-2 text-xs text-on-surface font-mono"
              value={scraperType}
              onChange={(e) => setScraperType(e.target.value)}
            >
              {TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* Schedule */}
          <div>
            <label className="text-[10px] font-mono text-on-surface/40 uppercase tracking-widest mb-1 block">
              Schedule
            </label>
            <select
              className="recessed-input rounded-lg w-full px-3 py-2 text-xs text-on-surface font-mono"
              value={schedulePreset}
              onChange={(e) => setSchedulePreset(e.target.value)}
            >
              {SCHEDULE_PRESETS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
            {schedulePreset === "__custom__" && (
              <input
                className="recessed-input rounded-lg w-full px-3 py-2 text-xs text-on-surface font-mono mt-2"
                value={customCron}
                onChange={(e) => setCustomCron(e.target.value)}
                placeholder="0 */6 * * *"
              />
            )}
          </div>

          {error && (
            <div className="text-red-400 text-[11px] font-mono">{error}</div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="text-[11px] font-mono text-on-surface/40 hover:text-on-surface/70 px-3 py-2"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="bg-primary/10 border border-primary/20 text-primary text-[11px] font-mono px-4 py-2 rounded-lg hover:bg-primary/20 transition-colors disabled:opacity-40"
            >
              {saving ? "Creating..." : "Add Scraper"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
