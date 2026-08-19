import axios from 'axios';
import {
  User,
  AuthResponse,
  Device,
  SensorReading,
  Incident,
  IncidentStatus,
  Alert,
  Hospital,
  HospitalNearest,
  Ambulance,
  AmbulanceNearest,
  AmbulanceStatus,
  Dispatch,
  DispatchStatus,
  WelfareCheck,
  WelfareCheckResponse,
  WelfareCheckStatus,
  WelfareMessages,
} from './types';

const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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

  // Hospitals
  getHospitals: async (params?: { is_active?: boolean }): Promise<Hospital[]> => {
    const res = await apiClient.get<Hospital[]>('/hospitals', { params });
    return res.data;
  },

  createHospital: async (data: { name: string; latitude: number; longitude: number; phone?: string }): Promise<Hospital> => {
    const res = await apiClient.post<Hospital>('/hospitals', data);
    return res.data;
  },

  getNearestHospitals: async (lat: number, lng: number, limit: number = 3): Promise<HospitalNearest[]> => {
    const res = await apiClient.get<HospitalNearest[]>('/hospitals/nearest', { params: { lat, lng, limit } });
    return res.data;
  },

  getHospital: async (id: string): Promise<Hospital> => {
    const res = await apiClient.get<Hospital>(`/hospitals/${id}`);
    return res.data;
  },

  // Ambulances
  getAmbulances: async (params?: { status?: AmbulanceStatus }): Promise<Ambulance[]> => {
    const res = await apiClient.get<Ambulance[]>('/ambulances', { params: { status_: params?.status } });
    return res.data;
  },

  createAmbulance: async (data: { ambulance_code: string; label?: string }): Promise<Ambulance> => {
    const res = await apiClient.post<Ambulance>('/ambulances', data);
    return res.data;
  },

  getNearestAmbulances: async (
    lat: number,
    lng: number,
    status: AmbulanceStatus = 'available',
    limit: number = 3
  ): Promise<AmbulanceNearest[]> => {
    const res = await apiClient.get<AmbulanceNearest[]>('/ambulances/nearest', {
      params: { lat, lng, status_: status, limit },
    });
    return res.data;
  },

  getAmbulance: async (identifier: string): Promise<Ambulance> => {
    const res = await apiClient.get<Ambulance>(`/ambulances/${identifier}`);
    return res.data;
  },

  // Dispatches
  createDispatch: async (incidentId: string, ambulanceId: string): Promise<Dispatch> => {
    const res = await apiClient.post<Dispatch>(`/incidents/${incidentId}/dispatch`, { ambulance_id: ambulanceId });
    return res.data;
  },

  updateDispatchStatus: async (dispatchId: string, status: DispatchStatus): Promise<Dispatch> => {
    const res = await apiClient.patch<Dispatch>(`/dispatches/${dispatchId}`, { status });
    return res.data;
  },

  getDispatches: async (params?: { incident_id?: string; ambulance_id?: string }): Promise<Dispatch[]> => {
    const res = await apiClient.get<Dispatch[]>('/dispatches', { params });
    return res.data;
  },

  getDispatch: async (dispatchId: string): Promise<Dispatch> => {
    const res = await apiClient.get<Dispatch>(`/dispatches/${dispatchId}`);
    return res.data;
  },

  // Welfare Checks
  getWelfareMessages: async (): Promise<WelfareMessages> => {
    const res = await apiClient.get<WelfareMessages>('/welfare-checks/config/messages');
    return res.data;
  },

  respondWelfareCheck: async (checkId: string, response: WelfareCheckResponse): Promise<WelfareCheck> => {
    const res = await apiClient.post<WelfareCheck>(`/welfare-checks/${checkId}/respond`, { response });
    return res.data;
  },

  getWelfareCheck: async (checkId: string): Promise<WelfareCheck> => {
    const res = await apiClient.get<WelfareCheck>(`/welfare-checks/${checkId}`);
    return res.data;
  },

  getWelfareCheckByDevice: async (deviceCode: string): Promise<WelfareCheck> => {
    const res = await apiClient.get<WelfareCheck>(`/welfare-checks/device/${deviceCode}`);
    return res.data;
  },

  getWelfareChecks: async (params?: { incident_id?: string; device_id?: string; status?: WelfareCheckStatus }): Promise<WelfareCheck[]> => {
    const res = await apiClient.get<WelfareCheck[]>('/welfare-checks', { params: { incident_id: params?.incident_id, device_id: params?.device_id, status_: params?.status } });
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
