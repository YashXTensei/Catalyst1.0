import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000,
});

export const apiService = {
  // Health
  getHealth: async () => {
    const res = await api.get('/health');
    return res.data;
  },

  // Repositories
  listRepositories: async () => {
    const res = await api.get('/repositories');
    return res.data;
  },

  connectRepository: async (url) => {
    const res = await api.post('/repositories/connect', { url });
    return res.data;
  },

  getRepositoryStatus: async (repoId) => {
    const res = await api.get(`/repositories/${repoId}/status`);
    return res.data;
  },

  triggerIndexing: async (repoId) => {
    const res = await api.post(`/repositories/${repoId}/index`);
    return res.data;
  },

  resetRepositoryStatus: async (repoId) => {
    const res = await api.post(`/repositories/${repoId}/reset-status`);
    return res.data;
  },

  getDecisions: async (repoId, params = {}) => {
    const res = await api.get(`/repositories/${repoId}/decisions`, { params });
    return res.data;
  },

  askQuestion: async (repoId, question) => {
    const res = await api.post(`/repositories/${repoId}/ask`, { question });
    return res.data;
  },

  analyzePR: async (repoId, prNumber) => {
    const res = await api.post(`/repositories/${repoId}/pull-requests/analyze`, { pr_number: parseInt(prNumber, 10) });
    return res.data;
  },

  simulatePR: async (repoId, payload) => {
    const res = await api.post(`/repositories/${repoId}/pull-requests/simulate`, payload);
    return res.data;
  },

  ingestDiscourse: async (repoId, payload) => {
    const res = await api.post(`/repositories/${repoId}/ingest-discourse`, payload);
    return res.data;
  },

  getBenchmarkResults: async () => {
    const res = await api.get('/benchmark');
    return res.data;
  },

  runLivePEPExtraction: async (pepNumber) => {
    const res = await api.post(`/benchmark/run-live?pep_number=${encodeURIComponent(pepNumber)}`);
    return res.data;
  },
};

export default apiService;
