import { useState, useEffect } from "react";
import { Icon } from "@iconify/react";
import { analyzeBuffered, fetchAnalysisHistory, fetchAnalysisDetail, startAnalysisUpload, fetchJobStatus } from "./api";

import RawLogsPanel from "./components/RawLogsPanel";
import Dashboard from "./components/Dashboard";

const severityClasses = {
  critical: "bg-red-500/10 text-red-400 border border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
  low: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
};

const tabs = ["Overview", "Root Cause", "Event Timeline", "Raw Logs", "Recommended Fixes"];

const mockAnalysis = {
  analysis_id: "ANL-1024",
  source: "jenkins",
  severity: "critical",
  summary: "Jenkins pipeline failed because Terraform state lock was not released.",
  root_cause: "Terraform apply step failed due to stale lock in remote backend.",
  recommendation: "Run terraform force-unlock and retry pipeline.",
  findings: [
    {
      plugin: "terraform",
      title: "Terraform State Lock",
      severity: "high",
      description: "State lock remained active for 18 minutes",
    },
  ],
  timeline: [
    { time: "12:41:02", event: "terraform apply started" },
    { time: "12:43:11", event: "state lock detected" },
  ],
  affected_resources: [{ name: "terraform-prod", type: "pipeline", risk: 9.1, plugin: "terraform" }],
  raw_logs: "terraform apply started\nERROR: Error acquiring the state lock\nLock info: ...",
  metadata: {
    plugin: "terraform_error",
    findings_count: 1,
    resources_count: 1,
    detected_at: new Date().toISOString(),
    correlation_score: 0.78,
    llm_confidence: 0.65,
    infra_risk: 0.72,
  },
};

function Sidebar({ analysisHistory, onSelect, onDashboard }) {
  const links = [{ label: "Dashboard", icon: "solar:widget-5-linear", action: onDashboard }];

  return (
    <aside className="w-64 border-r border-white/10 bg-[#0a0a0a] flex flex-col h-screen relative z-20 shrink-0">
      <div className="px-5 pt-6 mb-8 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-orange-500 shadow-glow"></div>
        <span className="text-zinc-100 font-medium tracking-tight text-base">DevOps Logs</span>
      </div>

      <div className="px-4 mb-6 flex gap-2">
        <button className="flex-1 bg-gradient-to-b from-orange-500 to-orange-600 text-white text-sm font-normal py-2 rounded-md shadow-glow transition-all flex items-center justify-center gap-2 border border-orange-400/20">
          <Icon icon="solar:add-circle-linear" className="text-lg" />
          New Analysis
        </button>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        <nav className="px-3 space-y-1 mb-6">
          {links.map((l) => (
            <button
              key={l.label}
              onClick={l.action}
              className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-normal text-zinc-400 hover:text-zinc-100 hover:bg-white/5 rounded-lg transition-colors"
            >
              <Icon icon={l.icon} className="text-lg opacity-70" />
              {l.label}
            </button>
          ))}
        </nav>

        <div className="px-5 text-[10px] text-zinc-500 uppercase tracking-[0.2em] font-bold mb-4">
          Analyses History
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-6 space-y-2">
          {!analysisHistory || !Array.isArray(analysisHistory) || analysisHistory.length === 0 ? (
            <div className="text-zinc-500 text-xs px-2 py-4 italic text-center border border-dashed border-white/5 rounded-lg">
              No analyses found in history
            </div>
          ) : (
            analysisHistory.map((a) => (
              <button
                key={a.analysis_id}
                onClick={() => onSelect(a.analysis_id)}
                className="w-full text-left px-3 py-3 rounded-xl bg-white/5 border border-white/5 hover:border-orange-500/40 hover:bg-white/10 transition-all group"
              >
                <div className="flex items-center justify-between text-xs text-zinc-200 mb-1.5">
                  <span className="font-mono font-medium text-orange-200/80 truncate pr-2">
                    {a.analysis_id?.split('-').pop() || "ANL"}
                  </span>
                  <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-white/5 text-zinc-400 border border-white/10">
                    {a.source || "log"}
                  </span>
                </div>
                <div className="text-[11px] text-zinc-400 line-clamp-2 leading-relaxed">
                  {a.summary || "No summary available"}
                </div>
              </button>
            ))
          )}
          
          {/* JSON Debug Dump (Internal use) */}
          {analysisHistory?.length > 0 && (
            <details className="mt-4 px-2">
              <summary className="text-[10px] text-zinc-700 cursor-pointer">Raw Data</summary>
              <pre className="text-[8px] text-zinc-600 overflow-hidden">
                {JSON.stringify(analysisHistory[0], null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </aside>
  );
}

function Header({ analysisId, onAnalyze, loading, onFileChange, source, setSource }) {
  return (
    <header className="h-16 flex items-center justify-between px-8 border-b border-white/5 z-10 shrink-0">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-zinc-500">Analyses</span>
        <span className="text-zinc-800">/</span>
        <span className="text-zinc-200">{analysisId || "Pending"}</span>
      </div>
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 px-3 py-1.5 text-sm border border-white/10 rounded-md bg-zinc-900/50 cursor-pointer">
          <Icon icon="solar:upload-linear" />
          <span className="text-zinc-200">Upload Logs</span>
          <input type="file" accept=".log,.txt,.json" className="hidden" onChange={onFileChange} />
        </label>
        <select
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="bg-zinc-900/50 border border-white/10 text-sm rounded-md px-3 py-1.5 text-zinc-200"
        >
          <option value="auto">Auto Detect</option>
          <option value="jenkins">Jenkins</option>
          <option value="kubernetes">Kubernetes</option>
          <option value="terraform">Terraform</option>
        </select>
        <button
          onClick={onAnalyze}
          disabled={loading}
          className="px-3 py-1.5 text-sm rounded-md border border-orange-500/40 bg-orange-500/10 text-orange-200 flex items-center gap-2 disabled:opacity-50"
        >
          {loading && <span className="w-2.5 h-2.5 rounded-full bg-orange-400 animate-ping" />}
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>
    </header>
  );
}

function SummaryCard({ data: analysis, activeTab, setActiveTab, selectedLogLine }) {
  return (
    <div className="bg-zinc-900/30 border border-white/5 rounded-xl overflow-hidden shadow-sm">
      <div className="p-6 pb-4 border-b border-white/5">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div>
            <h2 className="text-xl text-zinc-100 mb-4 flex items-center gap-3">
              Analysis {analysis?.analysis_id || "Pending"}
              <span
                className={`px-2 py-0.5 rounded-md text-xs ${
                  severityClasses[(analysis?.severity || "low").toLowerCase()] || severityClasses.low
                }`}
              >
                {analysis?.severity || "unknown"}
              </span>
            </h2>
            <p className="text-sm text-zinc-300 max-w-3xl">{analysis?.summary || "Upload logs to start analysis."}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-md border border-white/10 bg-zinc-800/50 text-zinc-300 text-sm flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-glow" />
              {analysis?.source || "auto"}
            </div>
          </div>
        </div>
      </div>
      <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="p-6">
        {activeTab === "Overview" && <p className="text-sm text-zinc-200">{analysis?.summary || "Upload logs to begin."}</p>}
        {activeTab === "Root Cause" && <p className="text-sm text-zinc-200">{analysis?.root_cause || "Pending."}</p>}
        {activeTab === "Event Timeline" && (
          <ul className="space-y-2 text-sm text-zinc-200">
            {(analysis?.timeline || []).map((e, idx) => (
              <li key={idx} className="flex gap-2 items-start">
                <span className="text-zinc-500 w-20">{e.time}</span>
                <span>{e.event}</span>
              </li>
            ))}
          </ul>
        )}
        {activeTab === "Raw Logs" && <RawLogsPanel rawLogs={analysis?.raw_logs || ""} selectedLine={selectedLogLine} />}
        {activeTab === "Recommended Fixes" && (
          <div className="space-y-4">
            {(() => {
              console.log("analysis state before render", analysis);
              console.log("analysis.structured_fix", analysis?.structured_fix);
              return analysis?.structured_fix ? (
                <StructuredFixCard fix={analysis.structured_fix} />
              ) : (
                <div className="recommendation-card">
                  <div className="label">Recommendation</div>
                  <p>{analysis?.recommendation || "No recommendation available."}</p>
                </div>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}

function StructuredFixCard({ fix }) {
  const [copied, setCopied] = useState(null);

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="bg-orange-500/5 border border-orange-500/20 rounded-xl p-6 shadow-glow-sm">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-orange-400 font-medium flex items-center gap-2">
          <Icon icon="solar:shield-check-bold" className="text-lg" />
          Structured Remediation
        </h3>
        {fix.reason && (
          <div className="px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 text-[10px] text-orange-300 uppercase tracking-widest font-bold">
            High Confidence
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <FixField
            label="Repository"
            value={fix.repository}
            icon="solar:glob-linear"
          />
          <FixField
            label="File Path"
            value={fix.file}
            icon="solar:file-text-linear"
            canCopy
            onCopy={() => copyToClipboard(fix.file, 'file')}
            isCopied={copied === 'file'}
          />
          <FixField
            label="Target Field"
            value={fix.field}
            icon="solar:tag-linear"
          />
        </div>
        <div className="space-y-4">
          <FixField
            label="Current Value"
            value={fix.current_value}
            icon="solar:history-linear"
            dimmed
          />
          <FixField
            label="Suggested Value"
            value={fix.suggested_value}
            icon="solar:magic-stick-3-bold"
            highlight
            canCopy
            onCopy={() => copyToClipboard(fix.suggested_value, 'value')}
            isCopied={copied === 'value'}
          />
        </div>
      </div>

      {fix.reason && (
        <div className="mt-6 pt-6 border-t border-orange-500/10">
          <p className="text-xs text-orange-300/60 uppercase tracking-widest mb-2 font-bold">Remediation Context</p>
          <p className="text-sm text-zinc-300 leading-relaxed italic">"{fix.reason}"</p>
        </div>
      )}
    </div>
  );
}

function FixField({ label, value, icon, canCopy, onCopy, isCopied, highlight, dimmed }) {
  if (!value) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold flex items-center gap-1.5">
        <Icon icon={icon} className="text-xs opacity-50" />
        {label}
      </p>
      <div className={`group flex items-center justify-between p-2.5 rounded-lg border ${
        highlight 
          ? 'bg-orange-500/10 border-orange-500/30 text-orange-200' 
          : 'bg-zinc-900/50 border-white/5 text-zinc-300'
      } ${dimmed ? 'opacity-60' : ''}`}>
        <code className="text-xs font-mono break-all">{value}</code>
        {canCopy && (
          <button 
            onClick={onCopy}
            className="ml-2 p-1.5 rounded hover:bg-white/10 text-zinc-500 hover:text-zinc-200 transition-colors shrink-0"
          >
            <Icon icon={isCopied ? "solar:check-read-linear" : "solar:copy-linear"} className={isCopied ? "text-emerald-400" : ""} />
          </button>
        )}
      </div>
    </div>
  );
}

function MetadataPanel({ data }) {
  return (
    <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-6">
      <h3 className="text-base text-zinc-100 mb-6">Analysis Metadata</h3>
      <div className="space-y-4 text-sm">
        <Row label="Source" value={data?.source || "—"} />
        <Row label="Plugin" value={data?.metadata?.plugin || "auto"} />
        <Row label="Severity" value={data?.severity || "—"} />
        <Row label="Findings" value={data?.metadata?.findings_count ?? data?.findings?.length ?? 0} />
        <Row label="Affected Resources" value={data?.metadata?.resources_count ?? data?.affected_resources?.length ?? 0} />
      </div>
    </div>
  );
}

const Row = ({ label, value }) => (
  <div className="flex justify-between items-center border-b border-white/5 pb-3 last:border-0 last:pb-0">
    <span className="text-zinc-500">{label}</span>
    <span className="text-zinc-200">{value}</span>
  </div>
);

function RadarCard({ data }) {
  const stats = {
    jenkins: Math.round((data?.metadata?.correlation_score ?? 0.6) * 100),
    kubernetes: 55,
    terraform: 78,
    risk: Math.round((data?.metadata?.infra_risk ?? 0.72) * 100),
    llm: Math.round((data?.metadata?.llm_confidence ?? 0.65) * 100),
  };
  return (
    <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-6 relative overflow-hidden shadow-sm">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-base text-zinc-100">Service Failure Map</h3>
        <div className="flex gap-4 text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>Current Impact
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>Risk
          </div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3 text-xs text-zinc-400 mb-4">
        <Metric label="Jenkins" value={stats.jenkins} />
        <Metric label="Kubernetes" value={stats.kubernetes} />
        <Metric label="Terraform" value={stats.terraform} />
        <Metric label="Infra Risk" value={stats.risk} />
        <Metric label="LLM Confidence" value={stats.llm} />
        <Metric label="Correlation" value={Math.round((data?.metadata?.correlation_score ?? 0.7) * 100)} />
      </div>
      <div className="w-full h-64 flex items-center justify-center relative mt-4">
        {/* reuse existing hexagon SVG */}
        <svg viewBox="0 0 200 200" className="w-64 h-64 overflow-visible">
          <polygon points="100,20 170,60 170,140 100,180 30,140 30,60" fill="none" stroke="rgba(255,255,255,0.05)" />
          <polygon points="100,40 152,70 152,130 100,160 48,130 48,70" fill="none" stroke="rgba(255,255,255,0.05)" />
          <polygon points="100,60 135,80 135,120 100,140 65,120 65,80" fill="none" stroke="rgba(255,255,255,0.05)" />
          <line x1="100" y1="100" x2="100" y2="20" stroke="rgba(255,255,255,0.05)" />
          <line x1="100" y1="100" x2="170" y2="60" stroke="rgba(255,255,255,0.05)" />
          <line x1="100" y1="100" x2="170" y2="140" stroke="rgba(255,255,255,0.05)" />
          <line x1="100" y1="100" x2="100" y2="180" stroke="rgba(255,255,255,0.05)" />
          <line x1="100" y1="100" x2="30" y2="140" stroke="rgba(255,255,255,0.05)" />
          <line x1="100" y1="100" x2="30" y2="60" stroke="rgba(255,255,255,0.05)" />
          <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgb(249,115,22)" stopOpacity="0.3" />
              <stop offset="100%" stopColor="rgb(234,88,12)" stopOpacity="0.05" />
            </linearGradient>
          </defs>
          <polygon
            points="100,30 160,70 135,125 100,170 40,135 60,65"
            fill="url(#grad1)"
            stroke="#f97316"
            className="drop-shadow-[0_0_8px_rgba(249,115,22,0.3)]"
          />
          <polygon points="100,45 145,75 160,135 100,150 50,130 55,75" fill="none" stroke="#ef4444" strokeDasharray="3,3" opacity="0.5" />
        </svg>
      </div>
    </div>
  );
}

const Metric = ({ label, value }) => (
  <div className="flex items-center gap-2 bg-white/5 border border-white/5 rounded-md px-3 py-2">
    <span className="text-zinc-300">{label}</span>
    <span className="text-zinc-100 font-medium">{value}%</span>
  </div>
);

function FindingsCard({ findings, onSelectLine }) {
  return (
    <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-base text-zinc-100">Detected Issues</h3>
      </div>
      <div className="space-y-3">
        {findings?.length ? (
          findings.map((f, idx) => (
            <div
              key={idx}
              className="border border-white/5 rounded-lg p-4 bg-white/5 cursor-pointer"
              onClick={() => f.line_number && onSelectLine && onSelectLine(f.line_number)}
            >
              <div className="flex items-center justify-between">
                <div className="text-zinc-200 text-sm">{f.title}</div>
                <span className={`text-xs px-2 py-0.5 rounded ${severityClasses[(f.severity || "").toLowerCase()] || severityClasses.low}`}>
                  {f.severity}
                </span>
              </div>
              <div className="text-xs text-zinc-500 mt-1">{f.plugin}</div>
              {f.line_number && (
                <button
                  className="mt-2 inline-flex items-center gap-2 text-xs text-orange-300 border border-orange-500/40 px-2 py-1 rounded bg-orange-500/10"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectLine && onSelectLine(f.line_number);
                  }}
                >
                  <Icon icon="solar:aim-bold" className="text-sm" />
                  Line {f.line_number}
                </button>
              )}
              <p className="text-sm text-zinc-300 mt-2">{f.description}</p>
            </div>
          ))
        ) : (
          <p className="text-sm text-zinc-500">No findings yet.</p>
        )}
      </div>
    </div>
  );
}

function ResourcesTable({ resources }) {
  return (
    <div className="bg-zinc-900/30 border border-white/5 rounded-xl p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-base text-zinc-100">Affected Services / Resources</h3>
      </div>
      <div className="w-full overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[500px]">
          <thead>
            <tr className="border-b border-white/5 text-xs text-zinc-500 uppercase">
              <th className="py-3 px-2">Resource Name</th>
              <th className="py-3 px-2">Type</th>
              <th className="py-3 px-2">Risk Score</th>
              <th className="py-3 px-2">Related Plugin</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {(resources || []).map((r, idx) => (
              <tr key={idx} className="border-b border-white/5 hover:bg-white/5">
                <td className="py-3 px-2 text-zinc-200">{r.name}</td>
                <td className="py-3 px-2 text-zinc-400">{r.type}</td>
                <td className="py-3 px-2 text-orange-400">{r.risk}</td>
                <td className="py-3 px-2 text-zinc-300">{r.plugin || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Tabs({ activeTab, setActiveTab }) {
  return (
    <>
      <div className="px-6 py-3 flex gap-2 items-center bg-black/20 border-b border-white/5">
        <div className="p-1 bg-zinc-900/60 border border-white/5 rounded-lg inline-flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 rounded-md text-sm ${
                activeTab === tab ? "bg-zinc-800 text-zinc-100" : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

export default function App() {
  const [analysis, setAnalysis] = useState(mockAnalysis);
  const [loading, setLoading] = useState(false);
  const [source, setSource] = useState("auto");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [activeTab, setActiveTab] = useState("Overview");
  const [selectedLogLine, setSelectedLogLine] = useState(null);
  const [activeView, setActiveView] = useState("dashboard"); // dashboard | analysis

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    setFile(f || null);
  };

  const handleAnalyze = async () => {
    setError("");
    setLoading(true);
    try {
      let response;
      if (file) {
        response = await startAnalysisUpload(file, source);
      } else {
        response = await analyzeBuffered();
      }

      if (response?.analysis) {
        const normalized = response.analysis;
        setAnalysis(normalized);
        setActiveView("analysis");
        loadHistory();
      } else {
        setAnalysis(null);
        setJobId(response.job_id);
        setJobStatus(response.status);
        setLoading(true);
      }
    } catch (err) {
      console.error(err);
      setError("Analysis failed. Check backend connection.");
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const data = await fetchAnalysisHistory();
      setAnalysisHistory(data);
    } catch (err) {
      console.error("Failed to load analysis history", err);
    }
  };

  const handleSelectAnalysis = async (analysisId) => {
    try {
      setLoading(true);
      setError("");
      const data = await fetchAnalysisDetail(analysisId);
      
      const normalized = data?.analysis ? data.analysis : data;

      setAnalysis(normalized);
      setSelectedLogLine(null);
      setActiveView("analysis");
    } catch (err) {
      console.error(err);
      if (err.response && err.response.status === 404) {
        setError("Analysis not found. It may have been deleted.");
        setTimeout(() => {
          setActiveView("dashboard");
          setError("");
        }, 3000);
      } else {
        setError("Failed to load analysis.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      try {
        const data = await fetchJobStatus(jobId);
        setJobStatus(data.status);

        if (data?.status === "completed" || data?.status === "finished") {
          const analysisId =
            data?.analysis?.analysis_id ||
            data?.analysis_id ||
            data?.analysis?.id ||
            data?.id;

          const fullAnalysis = await fetchAnalysisDetail(analysisId);

          console.log("job status response", data);
          console.log("full analysis response", fullAnalysis);

          const normalized = fullAnalysis?.analysis
            ? fullAnalysis.analysis
            : fullAnalysis;

          setAnalysis(normalized);
          setLoading(false);
          setJobId("");
          setJobStatus("");
          setSelectedLogLine(null);
          setActiveView("analysis");
          loadHistory();
          clearInterval(interval);
        } else if (data.status === "failed") {
          setError(data.error || "Job failed");
          setJobId("");
          setLoading(false);
          clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div className="h-screen flex overflow-hidden bg-ink">
      <Sidebar
        analysisHistory={analysisHistory}
        onSelect={handleSelectAnalysis}
        onDashboard={() => setActiveView("dashboard")}
      />
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-[500px] bg-orange-500/5 blur-[120px] pointer-events-none z-0" />
        <Header
          analysisId={analysis?.analysis_id}
          onAnalyze={handleAnalyze}
          loading={loading}
          onFileChange={handleFileChange}
          source={source}
          setSource={setSource}
        />
        <div className="flex-1 overflow-y-auto p-8 z-10 space-y-6">
          {error && <div className="border border-red-500/30 bg-red-500/10 text-red-200 text-sm px-4 py-2 rounded-md">{error}</div>}
          {jobId && (
            <div className="border border-orange-500/30 bg-orange-500/10 text-orange-100 text-sm px-4 py-2 rounded-md flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-400 animate-ping" />
              <span>Analyzing logs...</span>
              <span className="text-orange-200/80">Current step: {jobStatus || "queued"}</span>
            </div>
          )}
          {activeView === "dashboard" ? (
            <>
              <h1 className="text-2xl text-zinc-100">System Dashboard</h1>
              <Dashboard />
            </>
          ) : (
            <>
              <h1 className="text-2xl text-zinc-100">Analysis Detail</h1>
              <SummaryCard data={analysis} activeTab={activeTab} setActiveTab={setActiveTab} selectedLogLine={selectedLogLine} />
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-4 space-y-6">
                  <MetadataPanel data={analysis} />
                  <FindingsCard
                    findings={analysis?.findings}
                    onSelectLine={(line) => {
                      setSelectedLogLine(line);
                      setActiveTab("Raw Logs");
                    }}
                  />
                </div>
                <div className="lg:col-span-8 space-y-6">
                  <RadarCard data={analysis} />
                  <ResourcesTable resources={analysis?.affected_resources} />
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
