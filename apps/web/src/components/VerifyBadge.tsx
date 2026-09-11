const COLORS: Record<string, string> = {
  proven: "bg-emerald-600",
  verified_computation: "bg-emerald-600",
  numerically_confirmed: "bg-teal-600",
  strongly_supported: "bg-sky-600",
  heuristic: "bg-amber-600",
  hypothesis: "bg-orange-600",
  unverified: "bg-red-600",
  refuted: "bg-red-800",
};

export default function VerifyBadge({ level }: { level: string }) {
  const cls = COLORS[level] || "bg-gray-600";
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${cls}`}>
      {level.replace(/_/g, " ").toUpperCase()}
    </span>
  );
}
