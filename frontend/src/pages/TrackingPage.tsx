import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../lib/api-client';
import {
  ShieldAlert,
  Hospital,
  PhoneCall,
  Clock,
  MapPin,
  Truck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';

const incidentMarkerIcon = L.divIcon({
  className: 'custom-tracking-marker',
  html: `<div style="
    width: 36px;
    height: 36px;
    background: rgba(239, 68, 68, 0.2);
    border: 3px solid #ef4444;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 16px rgba(239, 68, 68, 0.7);
  ">
    <div style="width: 14px; height: 14px; background: #ef4444; border-radius: 50%;"></div>
  </div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
});

const ambulanceMarkerIcon = L.divIcon({
  className: 'custom-tracking-marker',
  html: `<div style="
    width: 38px;
    height: 38px;
    background: #0284c7;
    border: 2px solid #38bdf8;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    box-shadow: 0 0 16px rgba(56, 189, 248, 0.8);
  ">🚑</div>`,
  iconSize: [38, 38],
  iconAnchor: [19, 19],
});

export const TrackingPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();

  const {
    data: tracking,
    isLoading,
    isError,
    error,
    isFetching,
  } = useQuery({
    queryKey: ['publicTracking', token],
    queryFn: () => api.getTrackingInfo(token!),
    enabled: !!token,
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="text-center space-y-3 glass-card p-8 rounded-2xl border border-slate-800">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
          <p className="font-mono text-sm text-slate-300">Retrieving live emergency tracking data...</p>
        </div>
      </div>
    );
  }

  if (isError || !tracking) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full glass-card p-8 rounded-2xl border border-slate-800 text-center space-y-4">
          <div className="w-12 h-12 bg-red-500/10 border border-red-500/30 rounded-full flex items-center justify-center mx-auto text-red-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-100">Tracking Link Unavailable</h2>
          <p className="text-xs text-slate-400 leading-relaxed font-mono">
            {(error as any)?.response?.data?.detail || 'This tracking link is invalid, expired, or no longer exists.'}
          </p>
          <div className="pt-2 text-[11px] text-slate-500 font-mono">
            If this is an urgent emergency, please contact local emergency responders immediately.
          </div>
        </div>
      </div>
    );
  }

  const hasAmbulanceCoords =
    tracking.ambulance?.current_latitude != null && tracking.ambulance?.current_longitude != null;

  const mapCenter: [number, number] = hasAmbulanceCoords
    ? [
        (tracking.latitude + tracking.ambulance!.current_latitude!) / 2,
        (tracking.longitude + tracking.ambulance!.current_longitude!) / 2,
      ]
    : [tracking.latitude, tracking.longitude];

  const formatStatus = () => {
    if (tracking.status === 'resolved') {
      return {
        title: 'Emergency Incident Resolved',
        desc: 'Responders have secured the incident location.',
        bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
      };
    }
    if (tracking.dispatch_status === 'arrived') {
      return {
        title: 'Ambulance Arrived at Scene',
        desc: 'Emergency medical responders are on site assisting.',
        bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
      };
    }
    if (tracking.dispatch_status === 'dispatched' || tracking.dispatch_status === 'en_route') {
      return {
        title: 'Ambulance Dispatched & En Route',
        desc: 'Emergency vehicle is navigating towards the incident location.',
        bg: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400 animate-pulse',
      };
    }
    return {
      title: 'Emergency Incident Reported',
      desc: 'Smart accident response system is dispatching emergency units.',
      bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
    };
  };

  const statusInfo = formatStatus();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="bg-slate-900/80 border-b border-slate-800 px-4 py-3 sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            <div>
              <h1 className="text-sm font-bold text-slate-100">Live Emergency Status Tracking</h1>
              <p className="text-[11px] text-slate-400 font-mono">
                {tracking.owner_name ? `Vehicle Owner: ${tracking.owner_name}` : 'Public Emergency Feed'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 px-2.5 py-1 rounded-full">
            <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin' : ''}`} />
            <span>LIVE (5s)</span>
          </div>
        </div>
      </header>

      {/* Content Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 space-y-4">
        {/* Banner */}
        <div className={`p-4 rounded-2xl border ${statusInfo.bg} flex items-start gap-3`}>
          <CheckCircle2 className="w-5 h-5 mt-0.5 shrink-0" />
          <div>
            <h2 className="font-extrabold text-sm text-slate-100">{statusInfo.title}</h2>
            <p className="text-xs mt-0.5 opacity-90">{statusInfo.desc}</p>
          </div>
        </div>

        {/* Grid Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Incident Details Card */}
          <div className="glass-card rounded-2xl p-4 border border-slate-800 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400 flex items-center gap-1.5 font-bold uppercase text-[10px]">
                <MapPin className="w-3.5 h-3.5 text-red-400" /> Incident Location
              </span>
              <span className="text-[10px] text-slate-500">
                {new Date(tracking.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Event Type:</span>
                <span className="text-slate-200 capitalize">{tracking.incident_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Severity:</span>
                <span className="text-red-400 capitalize font-bold">{tracking.severity || 'Reported'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Coordinates:</span>
                <span className="text-slate-300">
                  {tracking.latitude.toFixed(4)}, {tracking.longitude.toFixed(4)}
                </span>
              </div>
            </div>
          </div>

          {/* Hospital Card */}
          <div className="glass-card rounded-2xl p-4 border border-slate-800 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400 flex items-center gap-1.5 font-bold uppercase text-[10px]">
                <Hospital className="w-3.5 h-3.5 text-emerald-400" /> Assigned Hospital
              </span>
            </div>
            {tracking.hospital ? (
              <div className="space-y-2">
                <div className="font-bold text-slate-100 text-sm">{tracking.hospital.name}</div>
                {tracking.hospital.phone && (
                  <a
                    href={`tel:${tracking.hospital.phone}`}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30 text-xs transition-colors"
                  >
                    <PhoneCall className="w-3.5 h-3.5" /> Call Hospital ({tracking.hospital.phone})
                  </a>
                )}
              </div>
            ) : (
              <div className="text-slate-500 italic text-[11px]">Calculating nearest emergency facility...</div>
            )}
          </div>
        </div>

        {/* Ambulance Unit Status */}
        {tracking.ambulance && (
          <div className="glass-card rounded-2xl p-4 border border-slate-800 space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400 flex items-center gap-1.5 font-bold uppercase text-[10px]">
                <Truck className="w-3.5 h-3.5 text-cyan-400" /> Assigned Medical Unit
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
                {tracking.ambulance.status}
              </span>
            </div>
            <div className="flex justify-between items-center text-slate-300">
              <span>Unit Identifier:</span>
              <span className="font-bold text-cyan-300">{tracking.ambulance.label || 'EMS Unit'}</span>
            </div>
          </div>
        )}

        {/* Leaflet Live Map */}
        <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden h-[340px] relative">
          <MapContainer center={mapCenter} zoom={13} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={[tracking.latitude, tracking.longitude]} icon={incidentMarkerIcon}>
              <Popup>
                <div className="font-mono text-xs">
                  <strong>Incident Location</strong>
                  <br />
                  {tracking.latitude.toFixed(5)}, {tracking.longitude.toFixed(5)}
                </div>
              </Popup>
            </Marker>

            {hasAmbulanceCoords && (
              <Marker
                position={[tracking.ambulance!.current_latitude!, tracking.ambulance!.current_longitude!]}
                icon={ambulanceMarkerIcon}
              >
                <Popup>
                  <div className="font-mono text-xs">
                    <strong>Ambulance Unit</strong>
                    <br />
                    Status: {tracking.ambulance!.status}
                  </div>
                </Popup>
              </Marker>
            )}
          </MapContainer>
        </div>
      </main>

      <footer className="text-center p-4 border-t border-slate-900 text-[10px] text-slate-500 font-mono">
        Smart Accident Response System &bull; Secure Emergency Public Feed &bull; Link valid for 24 hours
      </footer>
    </div>
  );
};

export default TrackingPage;
