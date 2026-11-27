import type { ReactNode } from "react";

export function StatCard({
  icon,
  label,
  value,
  change,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  change: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        {icon}
        <span>{label}</span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-change">{change}</div>
    </div>
  );
}
