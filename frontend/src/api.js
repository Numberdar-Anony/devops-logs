import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export async function analyzeBuffered() {
  const res = await axios.post(`${API_BASE}/analyze`, { use_ai: true });
  return res.data;
}

export async function fetchAnalysisHistory() {
  const res = await axios.get(`${API_BASE}/analyses`);
  return res.data;
}

export async function fetchAnalysisDetail(id) {
  const res = await axios.get(`${API_BASE}/analyses/${id}`);
  return res.data;
}

export async function fetchMetrics() {
  const res = await axios.get(`${API_BASE}/metrics`);
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
  const res = await axios.get(`${API_BASE}/jobs/${jobId}`);
  return res.data;
}
