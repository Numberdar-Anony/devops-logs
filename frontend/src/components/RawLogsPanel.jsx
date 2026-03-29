import { useEffect, useRef } from "react";

const highlightRules = [
  { regex: /(ERROR|FAIL|Exception|CrashLoopBackOff|ImagePullBackOff|OOMKilled|Permission denied)/i, className: "text-red-300" },
  { regex: /(WARN|Warning|Terraform state lock|timeout)/i, className: "text-orange-300" },
  { regex: /(retrying|fallback|degraded)/i, className: "text-yellow-200" },
];

export default function RawLogsPanel({ rawLogs, selectedLine }) {
  const containerRef = useRef(null);
  const lineRefs = useRef({});
  const lines = rawLogs ? rawLogs.split(/\r?\n/) : [];

  useEffect(() => {
    if (selectedLine && lineRefs.current[selectedLine]) {
      lineRefs.current[selectedLine].scrollIntoView({ behavior: "smooth", block: "center" });
      lineRefs.current[selectedLine].classList.add("border", "border-orange-500/60", "bg-orange-500/10", "shadow-glow");
      const timeout = setTimeout(() => {
        lineRefs.current[selectedLine]?.classList.remove("border", "border-orange-500/60", "bg-orange-500/10", "shadow-glow");
      }, 2000);
      return () => clearTimeout(timeout);
    }
  }, [selectedLine]);

  const decorate = (text) => {
    for (const rule of highlightRules) {
      if (rule.regex.test(text)) {
        return <span className={rule.className}>{text}</span>;
      }
    }
    return text;
  };

  return (
    <div ref={containerRef} className="bg-black/40 border border-white/5 rounded-lg text-xs font-mono text-zinc-200 h-96 overflow-auto">
      {lines.length === 0 && <div className="p-4 text-zinc-500">No raw logs available.</div>}
      {lines.map((line, idx) => {
        const lineNo = idx + 1;
        return (
          <div
            key={lineNo}
            ref={(el) => (lineRefs.current[lineNo] = el)}
            className="flex gap-3 px-4 py-1 border-b border-white/5 hover:bg-white/5"
          >
            <span className="text-zinc-500 w-12 text-right select-none">{lineNo}</span>
            <span className="whitespace-pre-wrap break-words flex-1">{decorate(line)}</span>
          </div>
        );
      })}
    </div>
  );
}
