import axios from 'axios';
import { User, AuthResponse, Device, SensorReading, Incident, IncidentStatus, Alert } from './types';

const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach Authorization Bearer token from localStorage
apiClient.interceptors.request.use((config) => {
  if (typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const api = {
  // Auth
  login: async (credentials: { email: string; password: string }): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>('/auth/login', credentials);
    return res.data;
  },

  getMe: async (): Promise<User> => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  // Devices
  getDevices: async (params?: { is_active?: boolean }): Promise<Device[]> => {
    const res = await apiClient.get<Device[]>('/devices', { params });
    return res.data;
  },

  createDevice: async (data: { device_code: string; device_type: 'simulator' | 'esp32'; label?: string }): Promise<Device> => {
    const res = await apiClient.post<Device>('/devices', data);
    return res.data;
  },

  getDevice: async (id: string): Promise<Device> => {
    const res = await apiClient.get<Device>(`/devices/${id}`);
    return res.data;
  },

  // Sensor Readings
  getReadings: async (params?: { device_id?: string; from?: string; to?: string; limit?: number }): Promise<SensorReading[]> => {
    const res = await apiClient.get<SensorReading[]>('/readings', { params });
    return res.data;
  },

  getLatestReadings: async (params?: { device_id?: string }): Promise<SensorReading[]> => {
    const res = await apiClient.get<SensorReading[]>('/readings/latest', { params });
    return res.data;
  },

  // Incidents
  getIncidents: async (params?: {
    status?: IncidentStatus;
    incident_type?: 'accident' | 'gas_leak';
    device_id?: string;
    sensor_reading_id?: string;
    from?: string;
    to?: string;
    limit?: number;
  }): Promise<Incident[]> => {
    const res = await apiClient.get<Incident[]>('/incidents', { params });
    return res.data;
  },

  getIncident: async (id: string): Promise<Incident> => {
    const res = await apiClient.get<Incident>(`/incidents/${id}`);
    return res.data;
  },

  updateIncidentStatus: async (id: string, status: IncidentStatus): Promise<Incident> => {
    const res = await apiClient.patch<Incident>(`/incidents/${id}`, { status });
    return res.data;
  },

  // Alerts
  getAlerts: async (params?: { incident_id?: string; limit?: number }): Promise<Alert[]> => {
    const res = await apiClient.get<Alert[]>('/alerts', { params });
    return res.data;
  },
};
