import React, { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useIncident, useIncidents, useUpdateIncidentStatus } from '../hooks/useIncidents';
import { useNearestAmbulances } from '../hooks/useAmbulances';
import { useDispatches, useCreateDispatch } from '../hooks/useDispatch';
import { useWelfareChecks } from '../hooks/useWelfareCheck';
import { annotateIncidentCoOccurrence } from '../lib/incident-utils';
import { StatusBadge } from '../components/StatusBadge';
import { IncidentStatus } from '../lib/types';
import { ArrowLeft, MapPin, CheckSquare, Activity, Bell, Navigation, Truck, Send, ShieldAlert, PhoneCall, CheckCircle2, HeartHandshake } from 'lucide-react';

export const IncidentDetailPage: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>();
  const { data: incident, isLoading, error } = useIncident(id);
  const { data: siblings = [] } = useIncidents(
    incident?.sensor_reading_id ? { sensor_reading_id: incident.sensor_reading_id } : undefined
  );
  const updateStatusMutation = useUpdateIncidentStatus();

  // Welfare Checks
  const { data: welfareChecks = [] } = useWelfareChecks(incident?.id ? { incident_id: incident.id } : undefined);
  const welfareCheck = welfareChecks.length > 0 ? welfareChecks[0] : null;

  // Ambulances & Dispatches
  const isAccident = incident?.incident_type === 'accident';
  const { data: nearestAmbulances = [], isLoading: isLoadingAmbulances } = useNearestAmbulances(
    isAccident ? incident?.latitude : undefined,
    isAccident ? incident?.longitude : undefined,
    'available',
    3
  );
  const { data: dispatches = [] } = useDispatches(incident?.id ? { incident_id: incident.id } : undefined);
  const createDispatchMutation = useCreateDispatch();

  // Active dispatch for this incident (if any)
  const activeDispatch = useMemo(() => {
    return dispatches.length > 0 ? dispatches[0] : null;
  }, [dispatches]);

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

  const handleDispatch = (ambulanceId: string) => {
    createDispatchMutation.mutate({ incidentId: incident.id, ambulanceId });
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

      {/* Welfare Check Panel (Sprint 3) */}
      {welfareCheck && (
        <div
          className={`glass-card rounded-2xl p-5 border ${
            welfareCheck.status === 'no_response_escalated' || welfareCheck.status === 'responded_help'
              ? 'border-rose-500/50 bg-rose-950/20 shadow-lg shadow-rose-950/40 animate-pulse'
              : welfareCheck.status === 'responded_ok'
              ? 'border-emerald-500/30 bg-emerald-950/10'
              : 'border-amber-500/30 bg-amber-950/10'
          } space-y-4`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2.5">
              <HeartHandshake className="w-5 h-5 text-cyan-400" />
              <h3 className="font-bold text-sm text-slate-100">Occupant Welfare Check & Escalation Status</h3>
            </div>
            <div className="flex items-center gap-2">
              {welfareCheck.status === 'no_response_escalated' && (
                <span className="px-3 py-1 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-mono font-bold uppercase flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 text-rose-400" /> ESCALATED — NO RESPONSE
                </span>
              )}
              {welfareCheck.status === 'responded_help' && (
                <span className="px-3 py-1 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-mono font-bold uppercase flex items-center gap-1.5">
                  <PhoneCall className="w-3.5 h-3.5 text-rose-400" /> HELP REQUESTED
                </span>
              )}
              {welfareCheck.status === 'responded_ok' && (
                <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold uppercase flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> RESPONDED OK
                </span>
              )}
              {welfareCheck.status === 'awaiting_response' && (
                <span className="px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-mono font-bold uppercase flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-amber-400 animate-spin" /> AWAITING RESPONSE
                </span>
              )}
            </div>
          </div>

          {(welfareCheck.status === 'no_response_escalated' || welfareCheck.status === 'responded_help') && (
            <div className="p-3.5 rounded-xl bg-rose-900/30 border border-rose-500/40 text-xs font-mono text-rose-200 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-rose-100 uppercase tracking-wide block font-bold mb-0.5">Elevated Urgency Alert:</strong>
                {welfareCheck.status === 'no_response_escalated'
                  ? 'No occupant response was received within 90 seconds. System has automatically escalated priority.'
                  : 'Vehicle occupant explicitly tapped "I NEED HELP". Prioritize immediate dispatch.'}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono text-slate-300 bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">Initiated At</span>
              <span>{new Date(welfareCheck.initiated_at).toLocaleTimeString()}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">Occupant Response</span>
              <span className="font-bold text-cyan-400">{welfareCheck.response ? welfareCheck.response.toUpperCase() : 'NONE'}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">Status Changed At</span>
              <span>
                {welfareCheck.responded_at
                  ? new Date(welfareCheck.responded_at).toLocaleTimeString()
                  : welfareCheck.escalated_at
                  ? new Date(welfareCheck.escalated_at).toLocaleTimeString()
                  : 'PENDING'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">In-Vehicle Tablet</span>
              <Link
                to={`/vehicle/${incident.device_id}`}
                target="_blank"
                className="text-cyan-400 hover:underline font-bold"
              >
                Open Vehicle Display &rarr;
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Ambulance Dispatch Panel (Accident Type Only) */}
      {isAccident && (
        <div className="glass-card rounded-2xl p-5 border border-emerald-500/30 bg-emerald-950/10 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
              <Truck className="w-4 h-4 text-emerald-400" />
              Nearest Available Ambulances & Dispatch Control
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Operator-Triggered Dispatch Only
            </span>
          </div>

          {activeDispatch ? (
            <div className="p-4 rounded-xl bg-slate-900/80 border border-amber-500/40 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-amber-400 flex items-center gap-2">
                  <Truck className="w-4 h-4" /> Active Dispatch Assigned
                </span>
                <span className="px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase font-bold text-[11px]">
                  Dispatch Status: {activeDispatch.status}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-slate-300">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Unit Code</span>
                  <span className="font-bold text-cyan-400">{activeDispatch.ambulance?.ambulance_code || activeDispatch.ambulance_id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Dispatched At</span>
                  <span>{new Date(activeDispatch.dispatched_at).toLocaleTimeString()}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Unit Tablet View</span>
                  <Link
                    to={`/ambulance/${activeDispatch.ambulance?.ambulance_code || activeDispatch.ambulance_id}`}
                    className="text-cyan-400 hover:underline font-bold"
                  >
                    Open Ambulance View &rarr;
                  </Link>
                </div>
              </div>
            </div>
          ) : isLoadingAmbulances ? (
            <div className="p-4 text-center font-mono text-xs text-slate-400">Calculating nearest available emergency units...</div>
          ) : nearestAmbulances.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400 text-center">
              No 'available' ambulances currently registered with location telemetry.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {nearestAmbulances.map((amb, index) => (
                <div
                  key={amb.id}
                  className="glass-card rounded-xl p-4 border border-slate-800 hover:border-emerald-500/40 transition-all flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/30">
                        #{index + 1} Nearest
                      </span>
                      <span className="text-emerald-400 font-bold text-sm">{amb.distance_km.toFixed(2)} km</span>
                    </div>
                    <div className="font-bold text-slate-100 text-base">{amb.ambulance_code}</div>
                    {amb.label && <div className="text-xs text-slate-400 font-mono">{amb.label}</div>}
                  </div>

                  <button
                    onClick={() => handleDispatch(amb.id)}
                    disabled={createDispatchMutation.isPending}
                    className="w-full py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <Send className="w-3.5 h-3.5" />
                    Dispatch This Ambulance
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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
