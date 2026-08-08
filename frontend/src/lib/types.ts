export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'operator' | string;
  is_active?: boolean;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Device {
  id: string;
  device_code: string;
  device_type: 'simulator' | 'esp32';
  label?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SensorReading {
  id: string;
  device_id: string;
  accel_x: number;
  accel_y: number;
  accel_z: number;
  gyro_x?: number | null;
  gyro_y?: number | null;
  gyro_z?: number | null;
  gas_level: number;
  latitude: number;
  longitude: number;
  recorded_at: string;
  received_at: string;
}

export type IncidentStatus = 'open' | 'acknowledged' | 'resolved' | 'false_positive';
export type IncidentType = 'accident' | 'gas_leak';
export type IncidentSeverity = 'minor' | 'moderate' | 'severe';

export interface Incident {
  id: string;
  device_id: string;
  sensor_reading_id: string;
  incident_type: IncidentType;
  severity?: IncidentSeverity | null;
  severity_score?: number | null;
  anomaly_score?: number | null;
  latitude: number;
  longitude: number;
  status: IncidentStatus;
  created_at: string;
  resolved_at?: string | null;
  sensor_reading?: SensorReading;
  alerts?: Alert[];
}

export interface Alert {
  id: string;
  incident_id: string;
  channel: 'mock' | 'email' | 'sms' | string;
  recipient?: string | null;
  payload: Record<string, any>;
  dispatched_at: string;
  delivery_status: 'mocked' | 'sent' | 'failed' | string;
}

export type WSMessage =
  | { type: 'reading'; data: SensorReading }
  | { type: 'incident'; data: Incident }
  | { type: 'alert'; data: Alert };

export interface AnnotatedIncident extends Incident {
  isCoOccurringGasLeak: boolean;
  displayTitle: string;
  badgeVariant: 'accident-severe' | 'accident-moderate' | 'accident-minor' | 'gas-critical' | 'gas-secondary';
}
