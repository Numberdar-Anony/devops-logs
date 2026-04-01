import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar } from "recharts";
import { fetchMetrics } from "../api";

const severityColors = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchMetrics()
      .then(setMetrics)
      .catch(() => setError("Failed to load metrics"));
  }, []);

  if (error) {
    return <div className="text-red-300">{error}</div>;
  }

  if (!metrics) {
    return <div className="text-zinc-400">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Total Analyses" value={metrics.total_analyses} />
        <StatCard label="Critical" value={metrics.critical} color="text-red-400" />
        <StatCard label="High" value={metrics.high} color="text-orange-300" />
        <StatCard label="Medium" value={metrics.medium} color="text-yellow-200" />
      </div>

      <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-4">
        <h3 className="text-zinc-100 text-sm mb-2">Analyses Over Time</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={metrics.analyses_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2f2f2f" />
              <XAxis dataKey="date" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", color: "#e5e7eb" }} />
              <Line type="monotone" dataKey="count" stroke="#f97316" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-4">
          <h3 className="text-zinc-100 text-sm mb-2">Severity Distribution</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={metrics.severity_distribution} dataKey="count" nameKey="severity" outerRadius={100} label>
                  {metrics.severity_distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={severityColors[entry.severity] || "#6b7280"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", color: "#e5e7eb" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-4">
          <h3 className="text-zinc-100 text-sm mb-2">Plugin Frequency</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.plugin_counts}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2f2f2f" />
                <XAxis dataKey="plugin" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", color: "#e5e7eb" }} />
                <Bar dataKey="count" fill="#f97316" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <InfoCard label="Top Plugin" value={metrics.top_plugin || "—"} />
        <InfoCard label="Top Issue" value={metrics.top_issue || "—"} />
        <InfoCard label="Top Source" value={metrics.top_source || "—"} />
      </div>
    </div>
  );
}

function StatCard({ label, value, color = "text-zinc-100" }) {
  return (
    <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-4">
      <p className="text-xs text-zinc-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-semibold ${color}`}>{value}</p>
    </div>
  );
}

function InfoCard({ label, value }) {
  return (
    <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-4">
      <p className="text-xs text-zinc-500 uppercase tracking-wide">{label}</p>
      <p className="text-lg text-zinc-100">{value}</p>
    </div>
  );
}
