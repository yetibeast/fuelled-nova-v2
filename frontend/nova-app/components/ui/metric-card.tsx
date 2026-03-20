"use client";

interface MetricCardProps {
  label: string;
  value: string;
  subtitle?: string;
  valueColor?: string;
  subtitleColor?: string;
}

export function MetricCard({ label, value, subtitle, valueColor = "text-white", subtitleColor = "text-secondary" }: MetricCardProps) {
  return (
    <div className="glass-card rounded-xl p-5">
      <div className="text-[10px] font-mono text-on-surface/40 uppercase tracking-widest mb-2">
        {label}
      </div>
      <div className={`text-2xl font-headline font-bold ${valueColor}`}>{value}</div>
      {subtitle && (
        <div className={`text-[10px] font-mono ${subtitleColor} mt-1`}>{subtitle}</div>
      )}
    </div>
  );
}
