import React, { useMemo } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useLiveFeed } from '../hooks/useLiveFeed';
import { useIncidents } from '../hooks/useIncidents';
import { useDevices } from '../hooks/useDevices';
import { annotateIncidentCoOccurrence } from '../lib/incident-utils';
import { MapView } from '../components/MapView';
import { IncidentCard } from '../components/IncidentCard';
import { Activity, Flame, ShieldAlert, Cpu, Radio, Bell } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { token } = useAuth();
  const { isConnected, latestReadings, recentReadings, liveIncidents, liveAlerts } = useLiveFeed(token);

  // Fetch REST historical incidents as base
  const { data: restIncidents = [] } = useIncidents({ limit: 50 });
  const { data: devices = [] } = useDevices();

  // Combine REST incidents and WebSocket live incidents (deduped by ID)
  const combinedIncidents = useMemo(() => {
    const map = new Map<string, any>();
    // First load REST incidents
    restIncidents.forEach((inc) => map.set(inc.id, inc));
    // Overlay WS incidents
    liveIncidents.forEach((inc) => map.set(inc.id, inc));

    const all = Array.from(map.values());
    // Sort newest first
    all.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return all;
  }, [restIncidents, liveIncidents]);

  // Apply the mandatory co-occurrence display rule!
  const annotatedIncidents = useMemo(() => {
    return annotateIncidentCoOccurrence(combinedIncidents);
  }, [combinedIncidents]);

  // Count active stats
  const activeDeviceCount = devices.filter((d) => d.is_active).length;
  const severeCrashCount = annotatedIncidents.filter((i) => i.badgeVariant === 'accident-severe').length;
  const standaloneGasLeakCount = annotatedIncidents.filter((i) => i.badgeVariant === 'gas-critical').length;
  const coOccurringGasCount = annotatedIncidents.filter((i) => i.isCoOccurringGasLeak).length;

  return (
    <div className="space-y-6">
      {/* Top Banner KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl p-4 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-mono font-semibold uppercase text-slate-400">Active Devices</p>
            <p className="text-2xl font-extrabold text-slate-100 mt-1">{activeDeviceCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Cpu className="w-6 h-6" />
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-mono font-semibold uppercase text-slate-400">Severe Accidents</p>
            <p className="text-2xl font-extrabold text-red-400 mt-1">{severeCrashCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-mono font-semibold uppercase text-slate-400">Standalone Gas Leaks</p>
            <p className="text-2xl font-extrabold text-purple-400 mt-1">{standaloneGasLeakCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Flame className="w-6 h-6" />
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-mono font-semibold uppercase text-slate-400">Co-occurring Gas Anomalies</p>
            <p className="text-2xl font-extrabold text-slate-300 mt-1">{coOccurringGasCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
            <Activity className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Grid: Telemetry Map + Live Incidents */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Live Radar Map & Telemetry Gauges */}
        <div className="lg:col-span-7 space-y-6">
          <MapView readings={Object.values(latestReadings)} incidents={combinedIncidents} />

          {/* Telemetry per device */}
          <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
                Live Sensor Telemetry per Device
              </h3>
              <span className="text-xs font-mono text-slate-500">
                Updated in real-time via WebSocket
              </span>
            </div>

            {Object.keys(latestReadings).length === 0 ? (
              <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 font-mono text-xs">
                No active device telemetry received yet. Run sensor simulator to publish data.
              </div>
            ) : (
              <div className="space-y-3">
                {Object.entries(latestReadings).map(([deviceId, rd]) => {
                  const mag = Math.sqrt(
                    Math.pow(rd.accel_x, 2) + Math.pow(rd.accel_y, 2) + Math.pow(rd.accel_z, 2)
                  );
                  return (
                    <div key={deviceId} className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 space-y-2">
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="font-bold text-cyan-400">Device ID: {deviceId}</span>
                        <span className="text-slate-400">{new Date(rd.recorded_at).toLocaleTimeString()}</span>
                      </div>

                      <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono bg-slate-950/60 p-2.5 rounded-lg border border-slate-900">
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase">Accel X/Y/Z</p>
                          <p className="font-semibold text-slate-200">
                            {rd.accel_x.toFixed(1)} / {rd.accel_y.toFixed(1)} / {rd.accel_z.toFixed(1)}
                          </p>
                        </div>
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase">Magnitude</p>
                          <p className={`font-bold ${mag > 2.5 ? 'text-red-400' : 'text-emerald-400'}`}>
                            {mag.toFixed(2)} g
                          </p>
                        </div>
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase">MQ-2 Gas</p>
                          <p className={`font-bold ${rd.gas_level > 200 ? 'text-purple-400' : 'text-slate-300'}`}>
                            {rd.gas_level.toFixed(0)} ppm
                          </p>
                        </div>
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase">GPS Pos</p>
                          <p className="font-semibold text-slate-300">
                            {rd.latitude.toFixed(3)}, {rd.longitude.toFixed(3)}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Live Incident Feed & Alerts Stream */}
        <div className="lg:col-span-5 space-y-6">
          {/* Incident Feed */}
          <div className="glass-card rounded-2xl p-5 border border-slate-800 flex flex-col h-[520px]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-400" />
                Live Incidents Feed
              </h3>
              <span className="text-xs font-mono text-cyan-400 font-semibold">
                {annotatedIncidents.length} Records
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pt-3 pr-1">
              {annotatedIncidents.length === 0 ? (
                <div className="p-8 text-center text-slate-500 font-mono text-xs">
                  No incidents detected. All system metrics nominal.
                </div>
              ) : (
                annotatedIncidents.map((incident) => (
                  <IncidentCard key={incident.id} incident={incident} />
                ))
              )}
            </div>
          </div>

          {/* Alert Stream */}
          <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-3">
            <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
              <Bell className="w-4 h-4 text-amber-400" />
              Live Emergency Alert Stream
            </h3>
            {liveAlerts.length === 0 ? (
              <p className="text-xs font-mono text-slate-500 italic">No alerts dispatched during this session.</p>
            ) : (
              <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                {liveAlerts.map((alt) => (
                  <div key={alt.id} className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs font-mono flex items-center justify-between">
                    <div>
                      <span className="text-amber-400 font-bold uppercase">[{alt.channel}]</span>{' '}
                      <span className="text-slate-300">Incident: {alt.incident_id.substring(0, 8)}...</span>
                    </div>
                    <span className="text-[10px] text-slate-500">{new Date(alt.dispatched_at).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
