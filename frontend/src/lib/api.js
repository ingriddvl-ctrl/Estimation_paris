import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const api = {
  searchAddress: (q) => axios.get(`${API}/address/search`, { params: { q } }).then(r => r.data),
  searchDVF: (lat, lon, radius = 500) => axios.get(`${API}/dvf/search`, { params: { lat, lon, radius } }).then(r => r.data),
  getGeoRisks: (lat, lon) => axios.get(`${API}/geo/risks`, { params: { lat, lon } }).then(r => r.data),
  estimateValuation: (data) => axios.post(`${API}/valuation/estimate`, data).then(r => r.data),
  saveValuation: (data) => axios.post(`${API}/valuation/save`, data).then(r => r.data),
  getValuation: (id) => axios.get(`${API}/valuation/${id}`).then(r => r.data),
  listValuations: () => axios.get(`${API}/valuations`).then(r => r.data),
  deleteValuation: (id) => axios.delete(`${API}/valuation/${id}`).then(r => r.data),
  getSharedValuation: (shareId) => axios.get(`${API}/share/${shareId}`).then(r => r.data),
  getAlgorithmConfig: () => axios.get(`${API}/algorithm/config`).then(r => r.data),
  updateAlgorithmConfig: (data) => axios.put(`${API}/algorithm/config`, data).then(r => r.data),
  calculateSimulation: (data) => axios.post(`${API}/simulation/calculate`, data).then(r => r.data),
  uploadDocument: (file, valuationId, category) => {
    const formData = new FormData();
    formData.append("file", file);
    return axios.post(`${API}/documents/upload?valuation_id=${valuationId || ""}&category=${category || "autre"}`, formData, {
      headers: { "Content-Type": "multipart/form-data" }
    }).then(r => r.data);
  },
  listDocuments: (valuationId) => axios.get(`${API}/documents/${valuationId}`).then(r => r.data),
  downloadDocument: (fileId) => axios.get(`${API}/documents/download/${fileId}`, { responseType: "blob" }).then(r => r),
  deleteDocument: (fileId) => axios.delete(`${API}/documents/${fileId}`).then(r => r.data),
  analyzeDocument: (fileId) => axios.post(`${API}/documents/analyze/${fileId}`).then(r => r.data),
  getMarketListings: (lat, lon, radius = 800) => axios.get(`${API}/market/listings`, { params: { lat, lon, radius } }).then(r => r.data),
  analyzeListing: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return axios.post(`${API}/listing/analyze`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    }).then(r => r.data);
  },
  recalculateValuation: (valuationId, excludedIds) => {
    return axios.post(`${API}/valuation/recalculate`, {
      valuation_id: valuationId,
      excluded_comparable_ids: excludedIds,
    }).then(r => r.data);
  },
  downloadPdfReport: (valuationId) => {
    return axios.get(`${API}/report/pdf/${valuationId}`, { responseType: "blob" }).then(r => {
      const url = window.URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const disposition = r.headers["content-disposition"] || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : `Estimation_${valuationId}.pdf`;
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    });
  },
  downloadListingPdf: (analysisId) => {
    return axios.get(`${API}/listing/report/pdf/${analysisId}`, { responseType: "blob" }).then(r => {
      const url = window.URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const disposition = r.headers["content-disposition"] || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : `Analyse_${analysisId}.pdf`;
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    });
  },
};
