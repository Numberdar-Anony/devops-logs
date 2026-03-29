import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function uploadLogs(file, source = "auto") {
  const form = new FormData();
  form.append("file", file);
  form.append("source", source);
  const res = await axios.post(`${API_BASE}/analyze/upload`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function analyzeBuffered() {
  const res = await axios.post(`${API_BASE}/analyze`, { use_ai: true });
  return res.data;
}

export async function fetchAnalyses() {
  const res = await axios.get(`${API_BASE}/api/analyses`);
  return res.data;
}

export async function fetchAnalysisDetail(id) {
  const res = await axios.get(`${API_BASE}/api/analyses/${id}`);
  return res.data;
}

export async function fetchMetrics() {
  const res = await axios.get(`${API_BASE}/api/metrics`);
  return res.data;
}

export async function startAnalysisUpload(file, source = "auto") {
  const form = new FormData();
  form.append("file", file);
  form.append("source", source);
  const res = await axios.post(`${API_BASE}/analyze/upload`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data; // {job_id, status}
}

export async function fetchJobStatus(jobId) {
  const res = await axios.get(`${API_BASE}/api/jobs/${jobId}`);
  return res.data;
}
