"use client";

const CURVES = [
  { name: "Compressor", factors: [100, 79, 59, 42, 28, 18, 14] },
  { name: "Separator", factors: [100, 81, 63, 45, 30, 20, 14] },
  { name: "Generator", factors: [100, 78, 58, 40, 25, 15, 12] },
  { name: "Tank", factors: [100, 76, 54, 35, 20, 12, 10] },
  { name: "Pump", factors: [100, 74, 52, 32, 20, 12, 10] },
  { name: "Pump Jack", factors: [100, 86, 72, 57, 42, 30, 20] },
  { name: "Truck", factors: [100, 74, 52, 38, 30, 22, 17] },
  { name: "Heavy Equip", factors: [100, 78, 58, 40, 25, 17, 15] },
];

const AGES = [0, 5, 10, 15, 20, 25, 30];

export function DepreciationTable() {
  return (
    <div className="glass-card rounded-xl p-6 mb-6">
      <h3 className="font-headline font-bold text-sm tracking-tight mb-1">Depreciation Curves</h3>
      <p className="text-[11px] font-mono text-on-surface/40 mb-4">
        Retention % at milestone ages — linear interpolation between points
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/30 border-b border-white/[0.05]">
            <tr>
              <th className="px-4 py-2">CATEGORY</th>
              {AGES.map((y) => <th key={y} className="px-3 py-2 text-right">{y}yr</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {CURVES.map((c) => (
              <tr key={c.name} className="hover:bg-white/[0.04] transition-colors">
                <td className="px-4 py-2 text-on-surface font-medium">{c.name}</td>
                {c.factors.map((f, i) => (
                  <td key={i} className={`px-3 py-2 text-right ${
                    f >= 70 ? "text-emerald-400" : f >= 40 ? "text-amber-400" : "text-red-400"
                  }`}>{f}%</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] font-mono text-on-surface/20 mt-2">Reference values — updated when gold tables change</p>
    </div>
  );
}
