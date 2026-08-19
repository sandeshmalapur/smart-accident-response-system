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

export interface Hospital {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  phone?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface HospitalNearest extends Hospital {
  distance_km: number;
}

export type AmbulanceStatus = 'available' | 'dispatched' | 'en_route' | 'at_scene' | 'offline';
export type DispatchStatus = 'dispatched' | 'en_route' | 'arrived' | 'completed' | 'cancelled';

export interface Ambulance {
  id: string;
  ambulance_code: string;
  label?: string | null;
  current_latitude?: number | null;
  current_longitude?: number | null;
  status: AmbulanceStatus;
  last_location_update?: string | null;
  created_at: string;
}

export interface AmbulanceNearest extends Ambulance {
  distance_km: number;
}

export interface Dispatch {
  id: string;
  incident_id: string;
  ambulance_id: string;
  dispatched_by: string;
  status: DispatchStatus;
  dispatched_at: string;
  updated_at: string;
  ambulance?: Ambulance | null;
  incident?: Incident | null;
}

export interface Incident {
  id: string;
  device_id: string;
  sensor_reading_id: string;
  nearest_hospital_id?: string | null;
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
  nearest_hospital?: Hospital | null;
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

export type WelfareCheckStatus = 'awaiting_response' | 'responded_ok' | 'responded_help' | 'no_response_escalated';
export type WelfareCheckResponse = 'ok' | 'help';

export interface WelfareCheck {
  id: string;
  incident_id: string;
  device_id: string;
  status: WelfareCheckStatus;
  initiated_at: string;
  responded_at?: string | null;
  response?: WelfareCheckResponse | null;
  escalated_at?: string | null;
  prompt?: string | null;
  safety_guidance?: string | null;
  escalation_notice?: string | null;
}

export interface WelfareMessages {
  prompt: string;
  safety_guidance: string;
  escalation_notice: string;
}

export type WSMessage =
  | { type: 'reading'; data: SensorReading }
  | { type: 'incident'; data: Incident }
  | { type: 'alert'; data: Alert }
  | { type: 'welfare_check'; data: WelfareCheck };

export interface AnnotatedIncident extends Incident {
  isCoOccurringGasLeak: boolean;
  displayTitle: string;
  badgeVariant: 'accident-severe' | 'accident-moderate' | 'accident-minor' | 'gas-critical' | 'gas-secondary';
}
