import { useState, useEffect } from "react";
import { Icon } from "@iconify/react";
import { analyzeBuffered, fetchAnalyses, fetchAnalysisDetail, startAnalysisUpload, fetchJobStatus } from "./api";
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

function Sidebar({ analyses, onSelect, onDashboard }) {
  const links = [{ label: "Dashboard", icon: "solar:widget-5-linear", action: onDashboard }];
  return (
    <aside className="w-64 flex-col border-r border-white/5 bg-[#0a0a0a] pt-6 pb-4 hidden md:flex h-full relative z-20">
      <div className="px-5 mb-8 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-orange-500 shadow-glow"></div>
        <span className="text-zinc-100 font-normal tracking-tight text-base">DevOps Logs</span>
      </div>
      <div className="px-4 mb-6 flex gap-2">
        <button className="flex-1 bg-gradient-to-b from-orange-500/90 to-orange-600/90 text-white text-sm font-normal py-2 rounded-md shadow-glow transition-all flex items-center justify-center gap-2 border border-orange-400/20">
          New Analysis
        </button>
        <button className="w-9 bg-zinc-800/30 text-zinc-400 rounded-md border border-white/5 flex items-center justify-center transition-colors">
          <Icon icon="solar:add-circle-linear" className="text-lg" />
        </button>
      </div>
      <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
        {links.map((l) => (
          <button
            key={l.label}
            onClick={l.action}
            className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-normal text-zinc-400 hover:text-zinc-100 hover:bg-white/5 rounded-lg"
          >
            <Icon icon={l.icon} className="text-lg opacity-70" />
            {l.label}
          </button>
        ))}
        <div className="text-xs text-zinc-500 uppercase tracking-wider mt-4 mb-2 px-2">Analyses</div>
        {(analyses || []).map((a) => (
          <button
            key={a.analysis_id}
            onClick={() => onSelect(a.analysis_id)}
            className="w-full text-left px-3 py-2.5 rounded-lg bg-white/5 border border-white/5 hover:border-orange-500/40 hover:text-zinc-100 transition-colors"
          >
            <div className="flex items-center justify-between text-sm text-zinc-200">
              <span>{a.analysis_id}</span>
              <span className="text-xs capitalize px-2 py-0.5 rounded border border-white/10 bg-white/5">{a.source || "unknown"}</span>
            </div>
            <div className="text-xs text-zinc-500 mt-1 capitalize">
              {a.severity || "n/a"} · {a.summary?.slice(0, 36) || "summary pending"}
            </div>
          </button>
        ))}
      </nav>
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

function SummaryCard({ data, activeTab, setActiveTab, selectedLogLine }) {
  return (
    <div className="bg-zinc-900/30 border border-white/5 rounded-xl overflow-hidden shadow-sm">
      <div className="p-6 pb-4 border-b border-white/5">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div>
            <h2 className="text-xl text-zinc-100 mb-4 flex items-center gap-3">
              Analysis {data?.analysis_id || "Pending"}
              <span
                className={`px-2 py-0.5 rounded-md text-xs ${
                  severityClasses[(data?.severity || "low").toLowerCase()] || severityClasses.low
                }`}
              >
                {data?.severity || "unknown"}
              </span>
            </h2>
            <p className="text-sm text-zinc-300 max-w-3xl">{data?.summary || "Upload logs to start analysis."}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-md border border-white/10 bg-zinc-800/50 text-zinc-300 text-sm flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-glow" />
              {data?.source || "auto"}
            </div>
          </div>
        </div>
      </div>
      <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="p-6">
        {activeTab === "Overview" && <p className="text-sm text-zinc-200">{data?.summary || "Upload logs to begin."}</p>}
        {activeTab === "Root Cause" && <p className="text-sm text-zinc-200">{data?.root_cause || "Pending."}</p>}
        {activeTab === "Event Timeline" && (
          <ul className="space-y-2 text-sm text-zinc-200">
            {(data?.timeline || []).map((e, idx) => (
              <li key={idx} className="flex gap-2 items-start">
                <span className="text-zinc-500 w-20">{e.time}</span>
                <span>{e.event}</span>
              </li>
            ))}
          </ul>
        )}
        {activeTab === "Raw Logs" && <RawLogsPanel rawLogs={data?.raw_logs || ""} selectedLine={selectedLogLine} />}
        {activeTab === "Recommended Fixes" && <p className="text-sm text-zinc-200">{data?.recommendation || "Pending."}</p>}
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
  const [analyses, setAnalyses] = useState([]);
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
      let resp;
      if (file) {
        const job = await startAnalysisUpload(file, source);
        setJobId(job.job_id);
        setJobStatus(job.status);
      } else {
        resp = await analyzeBuffered();
        setAnalysis(resp);
        loadAnalyses();
      }
    } catch (err) {
      console.error(err);
      setError("Analysis failed. Check backend connection.");
    } finally {
      setLoading(false);
    }
  };

  const loadAnalyses = async () => {
    try {
      const data = await fetchAnalyses();
      setAnalyses(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectAnalysis = async (analysisId) => {
    try {
      setLoading(true);
      const data = await fetchAnalysisDetail(analysisId);
      setAnalysis({
        analysis_id: data.analysis_id,
        source: data.source,
        severity: data.severity,
        summary: data.summary,
        root_cause: data.root_cause,
        recommendation: data.recommendation,
        findings: data.findings,
        timeline: data.raw_response_json?.timeline || [],
        affected_resources: data.affected_resources,
        raw_logs: data.raw_logs,
      });
      setSelectedLogLine(null);
      setActiveView("analysis");
    } catch (err) {
      console.error(err);
      setError("Failed to load analysis.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalyses();
  }, []);

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      try {
        const status = await fetchJobStatus(jobId);
        setJobStatus(status.status);
        if (status.status === "completed" && status.analysis_id) {
          const detail = await fetchAnalysisDetail(status.analysis_id);
          setAnalysis({
            analysis_id: detail.analysis_id,
            source: detail.source,
            severity: detail.severity,
            summary: detail.summary,
            root_cause: detail.root_cause,
            recommendation: detail.recommendation,
            findings: detail.findings,
            timeline: detail.raw_response_json?.timeline || [],
            affected_resources: detail.affected_resources,
            raw_logs: detail.raw_logs,
          });
          setJobId("");
          setJobStatus("");
          setSelectedLogLine(null);
          setActiveView("analysis");
          loadAnalyses();
        } else if (status.status === "failed") {
          setError(status.error || "Job failed");
          setJobId("");
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
        analyses={analyses}
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
          <h1 className="text-2xl text-zinc-100">Log Analysis</h1>
          {activeView === "dashboard" ? (
            <Dashboard />
          ) : (
            <>
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
