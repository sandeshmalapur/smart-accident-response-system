import React, { useState, useMemo, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Navigation,
  Radio,
  Building2,
  AlertTriangle,
  Cpu,
  Truck,
  Shield,
  Flame,
  Crosshair,
  Search,
  Eye,
  Activity,
  Layers,
  PhoneCall,
  Clock,
  ArrowUpRight,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useLiveFeed } from '../hooks/useLiveFeed';
import { useIncidents } from '../hooks/useIncidents';
import { useHospitals } from '../hooks/useHospitals';
import { useAmbulances } from '../hooks/useAmbulances';
import { useAgencyUnits } from '../hooks/useAgencyUnits';
import { useDevices } from '../hooks/useDevices';
import { Link } from 'react-router-dom';

// Haversine distance calculator
function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Custom Leaflet Icons
const policeIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="
    width: 36px;
    height: 36px;
    background: #1e3a8a;
    border: 2px solid #3b82f6;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    box-shadow: 0 0 16px rgba(59, 130, 246, 0.7);
    cursor: pointer;
  ">🚔</div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
});

const fireIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="
    width: 36px;
    height: 36px;
    background: #7f1d1d;
    border: 2px solid #ef4444;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    box-shadow: 0 0 16px rgba(239, 68, 68, 0.7);
    cursor: pointer;
  ">🚒</div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
});

const deviceIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="
    width: 28px;
    height: 28px;
    background: rgba(6, 182, 212, 0.25);
    border: 2px solid #06b6d4;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 14px rgba(6, 182, 212, 0.7);
  ">
    <div style="width: 10px; height: 10px; background: #06b6d4; border-radius: 50%;"></div>
  </div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

const hospitalIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="
    width: 36px;
    height: 36px;
    background: #064e3b;
    border: 2px solid #10b981;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    box-shadow: 0 0 16px rgba(16, 185, 129, 0.6);
    cursor: pointer;
  ">🏥</div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
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
      width: 38px;
      height: 38px;
      background: ${bg};
      border: 2.5px solid ${color};
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 0 18px ${color};
      cursor: pointer;
      transition: transform 0.2s ease;
    ">🚑</div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  });
}

function createIncidentIcon(severity?: string | null, incidentType?: string) {
  let color = '#f97316';
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
      width: 38px;
      height: 38px;
      background: ${bg};
      border: 2.5px solid ${color};
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      box-shadow: 0 0 20px ${color};
      cursor: pointer;
    ">
      ⚠️
    </div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  });
}

// Component to handle programmatic map center panning
const MapController: React.FC<{ targetCoords: [number, number] | null }> = ({ targetCoords }) => {
  const map = useMap();
  useEffect(() => {
    if (targetCoords) {
      map.flyTo(targetCoords, 15, { duration: 1.2 });
    }
  }, [targetCoords, map]);
  return null;
};

export const LiveMapPage: React.FC = () => {
  const { token } = useAuth();
  const { latestReadings, liveIncidents } = useLiveFeed(token);
  const { data: restIncidents = [] } = useIncidents({ limit: 50 });
  const { data: hospitals = [] } = useHospitals();
  const { data: ambulances = [] } = useAmbulances();
  const { data: agencyUnits = [] } = useAgencyUnits();
  const { data: devices = [] } = useDevices();

  // Combine incidents
  const combinedIncidents = useMemo(() => {
    const map = new Map<string, any>();
    restIncidents.forEach((inc) => map.set(inc.id, inc));
    liveIncidents.forEach((inc) => map.set(inc.id, inc));
    return Array.from(map.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [restIncidents, liveIncidents]);

  // Layer filter state
  const [showAmbulances, setShowAmbulances] = useState(true);
  const [showHospitals, setShowHospitals] = useState(true);
  const [showPolice, setShowPolice] = useState(true);
  const [showFire, setShowFire] = useState(true);
  const [showIncidents, setShowIncidents] = useState(true);
  const [showSensors, setShowSensors] = useState(true);

  // Search & Focus state
  const [searchQuery, setSearchQuery] = useState('');
  const [focusedCoords, setFocusedCoords] = useState<[number, number] | null>(null);
  const [activeTab, setActiveTab] = useState<'ambulances' | 'incidents' | 'hospitals' | 'agencies'>('ambulances');

  // Center map default (Bangalore coordinates)
  const defaultCenter: [number, number] = useMemo(() => {
    const activeAmb = ambulances.find((a) => a.current_latitude && a.current_longitude);
    if (activeAmb?.current_latitude && activeAmb?.current_longitude) {
      return [activeAmb.current_latitude, activeAmb.current_longitude];
    }
    if (hospitals.length > 0) {
      return [hospitals[0].latitude, hospitals[0].longitude];
    }
    return [12.9716, 77.5946];
  }, [ambulances, hospitals]);

  const activeAmbulances = ambulances.filter(
    (a) => a.current_latitude !== null && a.current_latitude !== undefined && a.current_longitude !== null && a.current_longitude !== undefined
  );

  const activeAgencies = agencyUnits.filter(
    (u) => u.current_latitude !== null && u.current_latitude !== undefined && u.current_longitude !== null && u.current_longitude !== undefined
  );

  const readingsList = Object.values(latestReadings);

  return (
    <div className="space-y-4">
      {/* Top Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card rounded-2xl p-4 border border-slate-800">
        <div>
          <h1 className="text-xl font-black text-slate-100 flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Navigation className="w-5 h-5 animate-pulse" />
            </span>
            Full-Screen GIS Command Center Map
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Real-time live telemetry tracking for Emergency Ambulances, Hospitals, Agencies & Road Incidents
          </p>
        </div>

        {/* Quick KPI stats */}
        <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
          <span className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1.5 font-bold">
            <Truck className="w-3.5 h-3.5" />
            {activeAmbulances.length} Ambulances Live
          </span>
          <span className="px-3 py-1.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-1.5 font-bold">
            <AlertTriangle className="w-3.5 h-3.5" />
            {combinedIncidents.filter((i) => i.status === 'open').length} Open Incidents
          </span>
          <span className="px-3 py-1.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center gap-1.5 font-bold">
            <Building2 className="w-3.5 h-3.5" />
            {hospitals.length} Hospitals
          </span>
        </div>
      </div>

      {/* Main Grid: Full Height Map & Live Fleet Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[calc(100vh-14rem)] min-h-[640px]">
        {/* Left Column (8 cols): The Large Leaflet Map Canvas */}
        <div className="lg:col-span-8 h-full flex flex-col glass-card rounded-2xl border border-slate-800 overflow-hidden relative shadow-2xl">
          {/* Map Layer Filter Pills (Floating Overlay) */}
          <div className="absolute top-4 left-4 z-[1000] bg-slate-950/90 backdrop-blur-md border border-slate-800 rounded-xl p-2 flex items-center gap-1.5 shadow-xl text-xs font-mono">
            <span className="text-slate-500 px-2 flex items-center gap-1">
              <Layers className="w-3.5 h-3.5 text-cyan-400" /> Layers:
            </span>
            <button
              onClick={() => setShowAmbulances(!showAmbulances)}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                showAmbulances ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-bold' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              🚑 Ambulances ({activeAmbulances.length})
            </button>
            <button
              onClick={() => setShowIncidents(!showIncidents)}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                showIncidents ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 font-bold' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              ⚠️ Incidents ({combinedIncidents.length})
            </button>
            <button
              onClick={() => setShowHospitals(!showHospitals)}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                showHospitals ? 'bg-teal-500/20 text-teal-400 border border-teal-500/40 font-bold' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              🏥 Hospitals ({hospitals.length})
            </button>
            <button
              onClick={() => {
                setShowPolice(!showPolice);
                setShowFire(!showFire);
              }}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                showPolice ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40 font-bold' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              🚔 Agencies ({activeAgencies.length})
            </button>
            <button
              onClick={() => setShowSensors(!showSensors)}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                showSensors ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 font-bold' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              📡 Sensors ({readingsList.length})
            </button>
          </div>

          {/* Leaflet Map */}
          <div className="flex-1 w-full h-full relative z-0">
            <MapContainer
              center={defaultCenter}
              zoom={13}
              style={{ width: '100%', height: '100%', background: '#020617' }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              <MapController targetCoords={focusedCoords} />

              {/* Sensor Node Markers */}
              {showSensors &&
                readingsList.map((reading) => (
                  <Marker key={reading.id} position={[reading.latitude, reading.longitude]} icon={deviceIcon}>
                    <Popup>
                      <div className="p-2 font-mono text-xs space-y-1 text-slate-900">
                        <div className="font-bold text-cyan-800 flex items-center gap-1">
                          <Cpu className="w-3.5 h-3.5" /> Sensor Telemetry Node
                        </div>
                        <div>Device ID: {reading.device_id.substring(0, 8)}...</div>
                        <div>GPS: {reading.latitude.toFixed(4)}°, {reading.longitude.toFixed(4)}°</div>
                        <div>Gas PPM: {reading.gas_level.toFixed(0)}</div>
                        <div className="text-[10px] text-slate-500">
                          {new Date(reading.recorded_at).toLocaleTimeString()}
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                ))}

              {/* Ambulance Markers */}
              {showAmbulances &&
                activeAmbulances.map((amb) => (
                  <Marker
                    key={amb.id}
                    position={[amb.current_latitude!, amb.current_longitude!]}
                    icon={createAmbulanceIcon(amb.status)}
                  >
                    <Popup>
                      <div className="p-2.5 font-mono text-xs space-y-1.5 text-slate-900 min-w-[200px]">
                        <div className="font-bold text-emerald-800 flex items-center justify-between border-b pb-1">
                          <span>🚑 {amb.ambulance_code}</span>
                          <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-900 text-[10px] uppercase font-bold">
                            {amb.status}
                          </span>
                        </div>
                        {amb.label && <div className="text-slate-700 font-medium">{amb.label}</div>}
                        <div>Lat/Lng: {amb.current_latitude!.toFixed(4)}°, {amb.current_longitude!.toFixed(4)}°</div>
                        {amb.last_location_update && (
                          <div className="text-[10px] text-slate-500">
                            Last Telemetry: {new Date(amb.last_location_update).toLocaleTimeString()}
                          </div>
                        )}
                        <div className="pt-1">
                          <Link
                            to={`/ambulance/${amb.ambulance_code}`}
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 hover:text-emerald-900 underline"
                          >
                            Open Driver Telemetry Cockpit &rarr;
                          </Link>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                ))}

              {/* Agency Units (Police & Fire) */}
              {showPolice &&
                activeAgencies.map((unit) => {
                  const isPolice = unit.agency_type === 'police';
                  if (!isPolice && !showFire) return null;
                  return (
                    <Marker
                      key={unit.id}
                      position={[unit.current_latitude!, unit.current_longitude!]}
                      icon={isPolice ? policeIcon : fireIcon}
                    >
                      <Popup>
                        <div className="p-2 font-mono text-xs space-y-1 text-slate-900">
                          <div className={`font-bold flex items-center gap-1 ${isPolice ? 'text-blue-800' : 'text-red-800'}`}>
                            {isPolice ? '🚔' : '🚒'} {unit.unit_code} ({unit.agency_type.toUpperCase()})
                          </div>
                          <div>Status: <span className="font-bold uppercase">{unit.status}</span></div>
                          {unit.label && <div>Label: {unit.label}</div>}
                          {unit.contact_phone && <div>Phone: {unit.contact_phone}</div>}
                          <div>GPS: {unit.current_latitude!.toFixed(4)}°, {unit.current_longitude!.toFixed(4)}°</div>
                        </div>
                      </Popup>
                    </Marker>
                  );
                })}

              {/* Hospitals */}
              {showHospitals &&
                hospitals.map((hosp) => (
                  <Marker key={hosp.id} position={[hosp.latitude, hosp.longitude]} icon={hospitalIcon}>
                    <Popup>
                      <div className="p-2 font-mono text-xs space-y-1 text-slate-900">
                        <div className="font-bold text-emerald-800 flex items-center gap-1">
                          🏥 {hosp.name}
                        </div>
                        <div>GPS: {hosp.latitude.toFixed(4)}°, {hosp.longitude.toFixed(4)}°</div>
                        {hosp.phone && <div>Emergency Hotline: {hosp.phone}</div>}
                        <div className="text-[10px] text-emerald-800 font-bold">Designated Trauma Facility</div>
                      </div>
                    </Popup>
                  </Marker>
                ))}

              {/* Incidents */}
              {showIncidents &&
                combinedIncidents.map((inc) => {
                  let nearestHospName = inc.nearest_hospital?.name || null;
                  let distKm: number | null = null;
                  if (inc.nearest_hospital) {
                    distKm = haversineKm(inc.latitude, inc.longitude, inc.nearest_hospital.latitude, inc.nearest_hospital.longitude);
                  }
                  return (
                    <Marker
                      key={inc.id}
                      position={[inc.latitude, inc.longitude]}
                      icon={createIncidentIcon(inc.severity, inc.incident_type)}
                    >
                      <Popup>
                        <div className="p-2.5 font-mono text-xs space-y-1.5 text-slate-900 min-w-[210px]">
                          <div className="font-bold text-rose-700 flex items-center justify-between border-b pb-1">
                            <span className="uppercase flex items-center gap-1">
                              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                              {inc.incident_type.replace('_', ' ')}
                            </span>
                            <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800">
                              {inc.severity || 'alert'}
                            </span>
                          </div>
                          <div>Status: <span className="font-bold uppercase text-slate-900">{inc.status}</span></div>
                          <div>GPS: {inc.latitude.toFixed(4)}°, {inc.longitude.toFixed(4)}°</div>
                          {nearestHospName && (
                            <div className="text-[11px] text-emerald-800 font-semibold border-t pt-1">
                              🏥 Nearest Hospital: {nearestHospName} {distKm && `(${distKm.toFixed(2)} km)`}
                            </div>
                          )}
                          <div className="pt-1">
                            <Link
                              to={`/incidents/${inc.id}`}
                              className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 hover:text-blue-900 underline"
                            >
                              Dispatch Emergency Units &rarr;
                            </Link>
                          </div>
                        </div>
                      </Popup>
                    </Marker>
                  );
                })}
            </MapContainer>
          </div>
        </div>

        {/* Right Column (4 cols): Live Fleet & Incident Navigation Panel */}
        <div className="lg:col-span-4 h-full flex flex-col glass-card rounded-2xl border border-slate-800 p-4 space-y-3 overflow-hidden shadow-2xl">
          {/* Navigation Tabs */}
          <div className="grid grid-cols-4 gap-1 p-1 bg-slate-900/90 rounded-xl border border-slate-800 text-[11px] font-mono">
            <button
              onClick={() => setActiveTab('ambulances')}
              className={`py-1.5 rounded-lg font-bold transition-all text-center flex items-center justify-center gap-1 ${
                activeTab === 'ambulances' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Truck className="w-3.5 h-3.5" />
              <span>Fleet</span>
            </button>
            <button
              onClick={() => setActiveTab('incidents')}
              className={`py-1.5 rounded-lg font-bold transition-all text-center flex items-center justify-center gap-1 ${
                activeTab === 'incidents' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Alerts</span>
            </button>
            <button
              onClick={() => setActiveTab('hospitals')}
              className={`py-1.5 rounded-lg font-bold transition-all text-center flex items-center justify-center gap-1 ${
                activeTab === 'hospitals' ? 'bg-teal-500/20 text-teal-400 border border-teal-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>Care</span>
            </button>
            <button
              onClick={() => setActiveTab('agencies')}
              className={`py-1.5 rounded-lg font-bold transition-all text-center flex items-center justify-center gap-1 ${
                activeTab === 'agencies' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Units</span>
            </button>
          </div>

          {/* Search box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search code, label, or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900/90 border border-slate-800 rounded-xl py-2 pl-8 pr-3 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Scrollable Items List with Focus / Fly-to Button */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {/* AMBULANCES TAB */}
            {activeTab === 'ambulances' && (
              <div className="space-y-2">
                {activeAmbulances.length === 0 ? (
                  <div className="p-6 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded-xl">
                    No active ambulances with GPS coordinates found. Run the seed script or simulator.
                  </div>
                ) : (
                  activeAmbulances
                    .filter(
                      (amb) =>
                        amb.ambulance_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (amb.label && amb.label.toLowerCase().includes(searchQuery.toLowerCase()))
                    )
                    .map((amb) => (
                      <div
                        key={amb.id}
                        className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-emerald-500/40 transition-all flex items-center justify-between group"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs font-mono text-emerald-400">
                              🚑 {amb.ambulance_code}
                            </span>
                            <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                              {amb.status}
                            </span>
                          </div>
                          {amb.label && <p className="text-[11px] text-slate-300 truncate max-w-[180px]">{amb.label}</p>}
                          <p className="text-[10px] font-mono text-slate-500">
                            GPS: {amb.current_latitude?.toFixed(4)}, {amb.current_longitude?.toFixed(4)}
                          </p>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => setFocusedCoords([amb.current_latitude!, amb.current_longitude!])}
                            title="Focus on Map"
                            className="p-2 rounded-lg bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-400 text-slate-400 border border-slate-700 transition-colors"
                          >
                            <Crosshair className="w-3.5 h-3.5" />
                          </button>
                          <Link
                            to={`/ambulance/${amb.ambulance_code}`}
                            title="Cockpit view"
                            className="p-2 rounded-lg bg-slate-800 hover:bg-emerald-500/20 hover:text-emerald-400 text-slate-400 border border-slate-700 transition-colors"
                          >
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </div>
                    ))
                )}
              </div>
            )}

            {/* INCIDENTS TAB */}
            {activeTab === 'incidents' && (
              <div className="space-y-2">
                {combinedIncidents.length === 0 ? (
                  <div className="p-6 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded-xl">
                    No recorded incidents on map.
                  </div>
                ) : (
                  combinedIncidents
                    .filter(
                      (inc) =>
                        inc.incident_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (inc.severity && inc.severity.toLowerCase().includes(searchQuery.toLowerCase()))
                    )
                    .map((inc) => (
                      <div
                        key={inc.id}
                        className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-amber-500/40 transition-all flex items-center justify-between group"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs font-mono text-amber-400 uppercase">
                              ⚠️ {inc.incident_type.replace('_', ' ')}
                            </span>
                            <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                              {inc.severity || 'alert'}
                            </span>
                          </div>
                          <p className="text-[10px] font-mono text-slate-400">
                            Status: <span className="uppercase text-slate-200">{inc.status}</span>
                          </p>
                          <p className="text-[10px] font-mono text-slate-500">
                            GPS: {inc.latitude.toFixed(4)}, {inc.longitude.toFixed(4)}
                          </p>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => setFocusedCoords([inc.latitude, inc.longitude])}
                            title="Focus on Map"
                            className="p-2 rounded-lg bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-400 text-slate-400 border border-slate-700 transition-colors"
                          >
                            <Crosshair className="w-3.5 h-3.5" />
                          </button>
                          <Link
                            to={`/incidents/${inc.id}`}
                            title="Dispatch Unit"
                            className="p-2 rounded-lg bg-slate-800 hover:bg-amber-500/20 hover:text-amber-400 text-slate-400 border border-slate-700 transition-colors"
                          >
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </div>
                    ))
                )}
              </div>
            )}

            {/* HOSPITALS TAB */}
            {activeTab === 'hospitals' && (
              <div className="space-y-2">
                {hospitals
                  .filter((h) => h.name.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map((hosp) => (
                    <div
                      key={hosp.id}
                      className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-teal-500/40 transition-all flex items-center justify-between"
                    >
                      <div className="space-y-1">
                        <span className="font-bold text-xs font-mono text-teal-400">🏥 {hosp.name}</span>
                        {hosp.phone && (
                          <p className="text-[10px] text-slate-400 flex items-center gap-1">
                            <PhoneCall className="w-3 h-3 text-teal-500" /> {hosp.phone}
                          </p>
                        )}
                        <p className="text-[10px] font-mono text-slate-500">
                          GPS: {hosp.latitude.toFixed(4)}, {hosp.longitude.toFixed(4)}
                        </p>
                      </div>

                      <button
                        onClick={() => setFocusedCoords([hosp.latitude, hosp.longitude])}
                        title="Focus on Map"
                        className="p-2 rounded-lg bg-slate-800 hover:bg-teal-500/20 hover:text-teal-400 text-slate-400 border border-slate-700 transition-colors"
                      >
                        <Crosshair className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
              </div>
            )}

            {/* AGENCIES TAB */}
            {activeTab === 'agencies' && (
              <div className="space-y-2">
                {activeAgencies
                  .filter(
                    (u) =>
                      u.unit_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      (u.label && u.label.toLowerCase().includes(searchQuery.toLowerCase()))
                  )
                  .map((unit) => {
                    const isPolice = unit.agency_type === 'police';
                    return (
                      <div
                        key={unit.id}
                        className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-blue-500/40 transition-all flex items-center justify-between"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className={`font-bold text-xs font-mono ${isPolice ? 'text-blue-400' : 'text-red-400'}`}>
                              {isPolice ? '🚔' : '🚒'} {unit.unit_code}
                            </span>
                            <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                              {unit.status}
                            </span>
                          </div>
                          {unit.label && <p className="text-[11px] text-slate-300">{unit.label}</p>}
                          {unit.contact_phone && (
                            <p className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
                              <PhoneCall className="w-3 h-3 text-slate-500" /> {unit.contact_phone}
                            </p>
                          )}
                        </div>

                        <button
                          onClick={() => setFocusedCoords([unit.current_latitude!, unit.current_longitude!])}
                          title="Focus on Map"
                          className="p-2 rounded-lg bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-400 text-slate-400 border border-slate-700 transition-colors"
                        >
                          <Crosshair className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    );
                  })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
