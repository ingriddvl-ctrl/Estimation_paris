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
};
