import React, { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useIncident, useIncidents, useUpdateIncidentStatus } from '../hooks/useIncidents';
import { annotateIncidentCoOccurrence } from '../lib/incident-utils';
import { StatusBadge } from '../components/StatusBadge';
import { IncidentStatus } from '../lib/types';
import { ArrowLeft, MapPin, Cpu, Clock, Bell, CheckSquare, Activity, Flame } from 'lucide-react';

export const IncidentDetailPage: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>();
  const { data: incident, isLoading, error } = useIncident(id);
  const { data: siblings = [] } = useIncidents(
    incident?.sensor_reading_id ? { sensor_reading_id: incident.sensor_reading_id } : undefined
  );
  const updateStatusMutation = useUpdateIncidentStatus();

  // Annotate co-occurrence including sibling incidents sharing the same sensor_reading_id
  const annotatedIncident = useMemo(() => {
    if (!incident) return null;
    const combined = [incident, ...siblings.filter((s) => s.id !== incident.id)];
    const annotatedList = annotateIncidentCoOccurrence(combined);
    return annotatedList.find((i) => i.id === incident.id) || null;
  }, [incident, siblings]);

  if (isLoading) {
    return (
      <div className="p-12 text-center text-cyan-400 font-mono text-sm">
        Loading incident dossier #{id}...
      </div>
    );
  }

  if (error || !incident || !annotatedIncident) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-red-400 font-mono text-sm">Incident not found or server error.</p>
        <Link to="/incidents" className="inline-flex items-center gap-2 text-xs font-mono text-cyan-400 hover:underline">
          <ArrowLeft className="w-4 h-4" /> Return to Incidents List
        </Link>
      </div>
    );
  }

  const handleStatusUpdate = (newStatus: IncidentStatus) => {
    updateStatusMutation.mutate({ id: incident.id, status: newStatus });
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Back Link & Title */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <Link
          to="/incidents"
          className="inline-flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-cyan-400 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Incident Records
        </Link>
        <span className="text-xs font-mono text-slate-500">UUID: {incident.id}</span>
      </div>

      {/* Main Incident Banner */}
      <div
        className={`glass-card rounded-2xl p-6 border ${
          annotatedIncident.isCoOccurringGasLeak
            ? 'border-slate-800 bg-slate-900/60'
            : annotatedIncident.badgeVariant === 'accident-severe'
            ? 'border-red-500/40 bg-red-950/20'
            : 'border-cyan-500/30'
        } space-y-4`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge variant={annotatedIncident.badgeVariant} size="lg" />
              <StatusBadge status={annotatedIncident.status} size="lg" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-100">{annotatedIncident.displayTitle}</h1>
          </div>

          {/* Status Mutation Action Dropdown */}
          <div className="glass-card rounded-xl p-3 border border-slate-800 flex items-center gap-3">
            <CheckSquare className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono text-slate-400 uppercase font-semibold">Triage Status:</span>
            <select
              value={incident.status}
              onChange={(e) => handleStatusUpdate(e.target.value as IncidentStatus)}
              disabled={updateStatusMutation.isPending}
              className="bg-slate-900 border border-slate-700 text-slate-100 text-xs font-mono rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
            >
              <option value="open">OPEN</option>
              <option value="acknowledged">ACKNOWLEDGED</option>
              <option value="resolved">RESOLVED</option>
              <option value="false_positive">FALSE POSITIVE</option>
            </select>
          </div>
        </div>

        {annotatedIncident.isCoOccurringGasLeak && (
          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs font-mono text-slate-300">
            <strong className="text-amber-400">Co-Occurrence Business Rule Applied:</strong> This gas anomaly row shared the same sensor reading ID with a severe crash incident. It is classified as a secondary anomaly caused by high acceleration magnitude spikes on the multivariate GMM model.
          </div>
        )}
      </div>

      {/* Grid: Sensor Reading Details & Alerts List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sensor Reading Snapshot */}
        <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-4">
          <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <Activity className="w-4 h-4 text-cyan-400" />
            Triggering Sensor Reading Snapshot
          </h3>

          {incident.sensor_reading ? (
            <div className="space-y-3 text-xs font-mono">
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-slate-400">Reading ID:</span>
                <span className="font-semibold text-cyan-300">{incident.sensor_reading.id}</span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-slate-400">Device Code:</span>
                <span className="font-semibold text-slate-200">{incident.device_id}</span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center bg-slate-950 p-3 rounded-lg border border-slate-900">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Accel Magnitude</span>
                  <span className="font-bold text-red-400 text-sm">
                    {Math.sqrt(
                      Math.pow(incident.sensor_reading.accel_x, 2) +
                        Math.pow(incident.sensor_reading.accel_y, 2) +
                        Math.pow(incident.sensor_reading.accel_z, 2)
                    ).toFixed(2)}{' '}
                    g
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">MQ-2 Gas Level</span>
                  <span className="font-bold text-purple-400 text-sm">{incident.sensor_reading.gas_level.toFixed(0)} ppm</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Recorded At</span>
                  <span className="font-bold text-slate-300 text-[11px]">
                    {new Date(incident.sensor_reading.recorded_at).toLocaleTimeString()}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2 text-rose-400">
                  <MapPin className="w-4 h-4" />
                  <span>GPS Location:</span>
                </div>
                <span className="font-bold text-slate-100">
                  {incident.latitude.toFixed(5)}° N, {incident.longitude.toFixed(5)}° E
                </span>
              </div>
            </div>
          ) : (
            <p className="text-xs font-mono text-slate-500 italic">No direct sensor reading payload attached.</p>
          )}
        </div>

        {/* Associated Dispatch Alerts */}
        <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-4">
          <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <Bell className="w-4 h-4 text-amber-400" />
            Notification Alerts Dispatch Log
          </h3>

          {!incident.alerts || incident.alerts.length === 0 ? (
            <p className="text-xs font-mono text-slate-500 italic">No alerts dispatched for this incident.</p>
          ) : (
            <div className="space-y-3">
              {incident.alerts.map((alt) => (
                <div key={alt.id} className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2 text-xs font-mono">
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 font-bold uppercase">
                      Channel: {alt.channel}
                    </span>
                    <span className="text-slate-500 text-[11px]">
                      {new Date(alt.dispatched_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-slate-300">
                    <span className="text-slate-500">Status:</span> {alt.delivery_status}
                  </div>
                  <pre className="bg-slate-950 p-2 rounded text-[10px] text-cyan-300 overflow-x-auto">
                    {JSON.stringify(alt.payload, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
