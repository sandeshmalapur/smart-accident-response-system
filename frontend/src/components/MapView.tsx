import React, { useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Navigation, Radio, Building2, AlertTriangle, Cpu, Truck, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SensorReading, Incident } from '../lib/types';
import { useHospitals } from '../hooks/useHospitals';
import { useAmbulances } from '../hooks/useAmbulances';
import { useDispatches } from '../hooks/useDispatch';
import { useAgencyUnits } from '../hooks/useAgencyUnits';

// Helper function to compute Haversine distance in JS for popup display
function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

const policeIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="
    width: 32px;
    height: 32px;
    background: #1e3a8a;
    border: 2px solid #3b82f6;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    box-shadow: 0 0 14px rgba(59, 130, 246, 0.6);
  ">🚔</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const fireIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="
    width: 32px;
    height: 32px;
    background: #7f1d1d;
    border: 2px solid #ef4444;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    box-shadow: 0 0 14px rgba(239, 68, 68, 0.6);
  ">🚒</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

// Leaflet DivIcons with HTML/SVG strings for reliable Vite rendering
const deviceIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="
    width: 28px;
    height: 28px;
    background: rgba(6, 182, 212, 0.2);
    border: 2px solid #06b6d4;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 12px rgba(6, 182, 212, 0.6);
  ">
    <div style="width: 10px; height: 10px; background: #06b6d4; border-radius: 50%;"></div>
  </div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

const hospitalIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="
    width: 32px;
    height: 32px;
    background: #064e3b;
    border: 2px solid #10b981;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #34d399;
    font-weight: bold;
    font-size: 16px;
    box-shadow: 0 0 14px rgba(16, 185, 129, 0.5);
  ">🏥</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

function createAmbulanceIcon(status: string) {
  let color = '#10b981'; // green default available
  let bg = '#064e3b';

  if (status === 'dispatched' || status === 'en_route') {
    color = '#f59e0b'; // amber
    bg = '#78350f';
  } else if (status === 'at_scene' || status === 'arrived') {
    color = '#f43f5e'; // red
    bg = '#881337';
  } else if (status === 'offline') {
    color = '#94a3b8'; // gray
    bg = '#1e293b';
  }

  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `<div style="
      width: 32px;
      height: 32px;
      background: ${bg};
      border: 2px solid ${color};
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      box-shadow: 0 0 14px ${color};
    ">🚑</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

function createIncidentIcon(severity?: string | null, incidentType?: string) {
  let color = '#f97316'; // orange default
  let bg = '#7c2d12';

  if (incidentType === 'gas_leak') {
    color = '#c084fc';
    bg = '#581c87';
  } else if (severity === 'severe') {
    color = '#f87171';
    bg = '#881337';
  } else if (severity === 'moderate') {
    color = '#fb923c';
    bg = '#7c2d12';
  } else if (severity === 'minor') {
    color = '#facc15';
    bg = '#713f12';
  }

  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `<div style="
      width: 32px;
      height: 32px;
      background: ${bg};
      border: 2px solid ${color};
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: ${color};
      font-weight: bold;
      box-shadow: 0 0 16px ${color};
    ">
      ⚠️
    </div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

interface MapViewProps {
  readings: SensorReading[];
  incidents: Incident[];
}

export const MapView: React.FC<MapViewProps> = ({ readings, incidents }) => {
  const { data: hospitals = [] } = useHospitals();
  const { data: ambulances = [] } = useAmbulances();
  const { data: agencyUnits = [] } = useAgencyUnits();
  const { data: dispatches = [] } = useDispatches();

  const activeDispatches = useMemo(() => {
    return dispatches.filter(
      (d) => d.status === 'dispatched' || d.status === 'en_route' || d.status === 'arrived'
    );
  }, [dispatches]);

  // Compute map center from readings, incidents, hospitals, ambulances, or fallback (Bangalore coordinates)
  const mapCenter = useMemo<[number, number]>(() => {
    if (incidents.length > 0) {
      return [incidents[0].latitude, incidents[0].longitude];
    }
    if (readings.length > 0) {
      return [readings[0].latitude, readings[0].longitude];
    }
    if (hospitals.length > 0) {
      return [hospitals[0].latitude, hospitals[0].longitude];
    }
    if (ambulances.length > 0 && ambulances[0].current_latitude && ambulances[0].current_longitude) {
      return [ambulances[0].current_latitude, ambulances[0].current_longitude];
    }
    return [12.9716, 77.5946];
  }, [readings, incidents, hospitals, ambulances]);

  return (
    <div className="glass-card rounded-2xl p-5 border border-slate-800 relative overflow-hidden flex flex-col h-[480px] space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Navigation className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-slate-100 uppercase tracking-wide">Live Operations Map</h3>
            <p className="text-xs text-slate-400 font-mono">Real-time Leaflet GIS Telemetry & Emergency Fleet Dispatch</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-cyan-400">
            <Radio className="w-3 h-3 animate-pulse" />
            {readings.length} Active Nodes
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-emerald-400">
            <Truck className="w-3 h-3" />
            {ambulances.length} Ambulances
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-emerald-400">
            <Building2 className="w-3 h-3" />
            {hospitals.length} Hospitals
          </span>
          <Link
            to="/map"
            className="flex items-center gap-1 px-3 py-1 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 font-bold transition-all shadow-sm shadow-cyan-500/10"
          >
            <span>Full Radar Map</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Leaflet Container */}
      <div className="flex-1 w-full rounded-xl overflow-hidden border border-slate-800 z-0">
        <MapContainer center={mapCenter} zoom={13} style={{ width: '100%', height: '100%', background: '#020617' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Active Device / Reading Markers */}
          {readings.map((reading) => (
            <Marker key={reading.id} position={[reading.latitude, reading.longitude]} icon={deviceIcon}>
              <Popup className="leaflet-popup-dark">
                <div className="p-2 font-mono text-xs space-y-1 text-slate-900">
                  <div className="font-bold text-cyan-700 flex items-center gap-1">
                    <Cpu className="w-3.5 h-3.5" /> Sensor Device Node
                  </div>
                  <div>ID: {reading.device_id.substring(0, 8)}...</div>
                  <div>
                    GPS: {reading.latitude.toFixed(4)}°, {reading.longitude.toFixed(4)}°
                  </div>
                  <div>Gas Level: {reading.gas_level.toFixed(0)} ppm</div>
                  <div className="text-[10px] text-slate-500">
                    Recorded: {new Date(reading.recorded_at).toLocaleTimeString()}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Active Dispatch Navigation Polylines */}
          {activeDispatches.map((disp) => {
            const amb = ambulances.find((a) => a.id === disp.ambulance_id);
            const inc = incidents.find((i) => i.id === disp.incident_id);
            if (
              !amb ||
              !inc ||
              amb.current_latitude == null ||
              amb.current_longitude == null ||
              inc.latitude == null ||
              inc.longitude == null
            ) {
              return null;
            }

            const isArrived = disp.status === 'arrived';
            return (
              <Polyline
                key={`dash-nav-${disp.id}`}
                positions={[
                  [amb.current_latitude, amb.current_longitude],
                  [inc.latitude, inc.longitude],
                ]}
                pathOptions={{
                  color: isArrived ? '#10b981' : '#f59e0b',
                  weight: 3.5,
                  opacity: 0.85,
                  dashArray: isArrived ? undefined : '6, 6',
                }}
              />
            );
          })}

          {/* Ambulance Markers */}
          {ambulances
            .filter((amb) => amb.current_latitude !== null && amb.current_latitude !== undefined && amb.current_longitude !== null && amb.current_longitude !== undefined)
            .map((amb) => (
              <Marker
                key={amb.id}
                position={[amb.current_latitude!, amb.current_longitude!]}
                icon={createAmbulanceIcon(amb.status)}
              >
                <Popup>
                  <div className="p-2 font-mono text-xs space-y-1 text-slate-900">
                    <div className="font-bold text-emerald-800 flex items-center gap-1">
                      🚑 {amb.ambulance_code} {amb.label ? `(${amb.label})` : ''}
                    </div>
                    <div>
                      Status: <span className="font-bold uppercase text-slate-900">{amb.status}</span>
                    </div>
                    <div>
                      Coordinates: {amb.current_latitude!.toFixed(4)}°, {amb.current_longitude!.toFixed(4)}°
                    </div>
                    {amb.last_location_update && (
                      <div className="text-[10px] text-slate-500">
                        Telemetry: {new Date(amb.last_location_update).toLocaleTimeString()}
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}

          {/* Agency Unit Markers (Police & Fire) */}
          {agencyUnits
            .filter((unit) => unit.current_latitude !== null && unit.current_latitude !== undefined && unit.current_longitude !== null && unit.current_longitude !== undefined)
            .map((unit) => {
              const isPolice = unit.agency_type === 'police';
              return (
                <Marker
                  key={unit.id}
                  position={[unit.current_latitude!, unit.current_longitude!]}
                  icon={isPolice ? policeIcon : fireIcon}
                >
                  <Popup>
                    <div className="p-2 font-mono text-xs space-y-1 text-slate-900">
                      <div className={`font-bold flex items-center gap-1 ${isPolice ? 'text-blue-700' : 'text-red-700'}`}>
                        {isPolice ? '🚔' : '🚒'} {unit.unit_code} ({unit.agency_type.toUpperCase()})
                      </div>
                      <div>
                        Status: <span className="font-bold uppercase text-slate-800">{unit.status}</span>
                      </div>
                      {unit.label && <div>Label: {unit.label}</div>}
                      {unit.contact_phone && <div>Phone: {unit.contact_phone}</div>}
                      <div>
                        Coordinates: {unit.current_latitude!.toFixed(4)}°, {unit.current_longitude!.toFixed(4)}°
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            })}

          {/* Hospital Markers */}
          {hospitals.map((hosp) => (
            <Marker key={hosp.id} position={[hosp.latitude, hosp.longitude]} icon={hospitalIcon}>
              <Popup>
                <div className="p-2 font-mono text-xs space-y-1 text-slate-900">
                  <div className="font-bold text-emerald-700 flex items-center gap-1">
                    🏥 {hosp.name}
                  </div>
                  <div>
                    GPS: {hosp.latitude.toFixed(4)}°, {hosp.longitude.toFixed(4)}°
                  </div>
                  {hosp.phone && <div>Phone: {hosp.phone}</div>}
                  <div className="text-[10px] text-emerald-800 font-semibold">Registered Trauma Center</div>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Incident Markers */}
          {incidents.map((inc) => {
            // Determine nearest hospital info
            let nearestHospitalName = inc.nearest_hospital?.name || null;
            let nearestDistKm: number | null = null;

            if (inc.nearest_hospital) {
              nearestDistKm = haversineKm(
                inc.latitude,
                inc.longitude,
                inc.nearest_hospital.latitude,
                inc.nearest_hospital.longitude
              );
            } else if (hospitals.length > 0) {
              // Fallback compute nearest hospital from loaded hospitals array
              let minDist = Infinity;
              let bestHospName = '';
              for (const h of hospitals) {
                const d = haversineKm(inc.latitude, inc.longitude, h.latitude, h.longitude);
                if (d < minDist) {
                  minDist = d;
                  bestHospName = h.name;
                }
              }
              if (minDist !== Infinity) {
                nearestHospitalName = bestHospName;
                nearestDistKm = minDist;
              }
            }

            return (
              <Marker
                key={inc.id}
                position={[inc.latitude, inc.longitude]}
                icon={createIncidentIcon(inc.severity, inc.incident_type)}
              >
                <Popup>
                  <div className="p-2 font-mono text-xs space-y-1.5 text-slate-900">
                    <div className="font-bold text-rose-700 flex items-center gap-1 uppercase">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      {inc.incident_type.replace('_', ' ')} ({inc.severity || 'anomaly'})
                    </div>
                    <div>Status: <span className="font-bold uppercase text-slate-800">{inc.status}</span></div>
                    <div>
                      Coordinates: {inc.latitude.toFixed(4)}°, {inc.longitude.toFixed(4)}°
                    </div>

                    <div className="border-t border-slate-300 pt-1 text-[11px]">
                      <div className="font-bold text-slate-800">Nearest Hospital:</div>
                      {nearestHospitalName ? (
                        <div className="text-emerald-800 font-semibold">
                          🏥 {nearestHospitalName}{' '}
                          {nearestDistKm !== null && `(${nearestDistKm.toFixed(2)} km away)`}
                        </div>
                      ) : (
                        <div className="text-slate-500 italic">No active hospital registered</div>
                      )}
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-t border-slate-800/80 pt-2 z-10">
        <span>Active Incidents: {incidents.filter((i) => i.status === 'open').length}</span>
        <span className="text-cyan-400">OpenStreetMap Interactive Tiles</span>
      </div>
    </div>
  );
};
