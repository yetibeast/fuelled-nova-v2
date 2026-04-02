"use client";

const BENCHMARKS = [
  { category: "Reciprocating Compressor", base_hp: 100, base_rcn: "$100,000", scaling: "HP^0.6" },
  { category: "Screw Compressor", base_hp: 100, base_rcn: "$80,000", scaling: "HP^0.6" },
  { category: "Centrifugal Compressor", base_hp: 500, base_rcn: "$160,000", scaling: "HP^0.6" },
  { category: "Centrifugal Pump", base_hp: 50, base_rcn: "$22,000", scaling: "HP^0.6" },
  { category: "PD Pump", base_hp: 50, base_rcn: "$38,000", scaling: "HP^0.6" },
  { category: "Diesel Generator", base_hp: 100, base_rcn: "$60,000", scaling: "HP^0.6" },
  { category: "NG Generator", base_hp: 100, base_rcn: "$75,000", scaling: "HP^0.6" },
];

export function RcnBenchmarks() {
  return (
    <div className="glass-card rounded-xl p-6 mb-6">
      <h3 className="font-headline font-bold text-sm tracking-tight mb-1">
        RCN Base Values &amp; HP Scaling
      </h3>
      <p className="text-[11px] font-mono text-on-surface/40 mb-4">
        Formula: Base RCN x (Actual HP / Base HP)^0.6
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/30 border-b border-white/[0.05]">
            <tr>
              <th className="px-4 py-2">EQUIPMENT</th>
              <th className="px-4 py-2 text-right">BASE HP</th>
              <th className="px-4 py-2 text-right">BASE RCN</th>
              <th className="px-4 py-2 text-right">SCALING</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {BENCHMARKS.map((b) => (
              <tr key={b.category} className="hover:bg-white/[0.04] transition-colors">
                <td className="px-4 py-2 text-on-surface font-medium">{b.category}</td>
                <td className="px-4 py-2 text-right text-on-surface/70">{b.base_hp}</td>
                <td className="px-4 py-2 text-right text-secondary font-bold">{b.base_rcn}</td>
                <td className="px-4 py-2 text-right text-on-surface/50">{b.scaling}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] font-mono text-on-surface/20 mt-2">Reference values — updated when gold tables change</p>
    </div>
  );
}
