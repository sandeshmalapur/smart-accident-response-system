import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAmbulance } from '../hooks/useAmbulances';
import { useDispatches, useUpdateDispatchStatus } from '../hooks/useDispatch';
import { Truck, MapPin, AlertTriangle, CheckCircle, Navigation, Shield, ArrowLeft } from 'lucide-react';

export const AmbulanceView: React.FC = () => {
  const { ambulanceCode = '' } = useParams<{ ambulanceCode: string }>();
  const { data: ambulance, isLoading: isLoadingAmb } = useAmbulance(ambulanceCode);
  const { data: dispatches = [], isLoading: isLoadingDisp } = useDispatches(
    ambulance?.id ? { ambulance_id: ambulance.id } : undefined
  );
  const updateStatusMutation = useUpdateDispatchStatus();

  // Find active dispatch (not completed or cancelled)
  const activeDispatch = dispatches.find(
    (d) => d.status === 'dispatched' || d.status === 'en_route' || d.status === 'arrived'
  );

  if (isLoadingAmb || isLoadingDisp) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6 text-cyan-400 font-mono text-sm">
        Initializing Emergency Vehicle Telemetry Tablet [{ambulanceCode}]...
      </div>
    );
  }

  if (!ambulance) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 space-y-4 text-center">
        <p className="text-red-400 font-mono text-sm">Ambulance code '{ambulanceCode}' not registered in fleet database.</p>
        <Link to="/dashboard" className="text-xs font-mono text-cyan-400 hover:underline">
          Return to Operations Dashboard
        </Link>
      </div>
    );
  }

  const handleUpdateStatus = (newStatus: 'en_route' | 'arrived' | 'completed') => {
    if (activeDispatch) {
      updateStatusMutation.mutate({ dispatchId: activeDispatch.id, status: newStatus });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col p-4 md:p-8 space-y-6">
      {/* Ambulance Vehicle Tablet Header */}
      <header className="glass-card rounded-2xl p-6 border border-cyan-500/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
            <Truck className="w-8 h-8" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-slate-100 tracking-wide">{ambulance.ambulance_code}</h1>
              <span
                className={`px-3 py-1 rounded-full text-xs font-mono font-bold uppercase border ${
                  ambulance.status === 'available'
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                    : ambulance.status === 'dispatched' || ambulance.status === 'en_route'
                    ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 animate-pulse'
                    : ambulance.status === 'at_scene'
                    ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                Unit Status: {ambulance.status}
              </span>
            </div>
            {ambulance.label && <p className="text-xs font-mono text-slate-400">{ambulance.label}</p>}
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <div className="text-right">
            <span className="block text-[10px] text-slate-500 uppercase">Current Telemetry GPS</span>
            <span className="font-bold text-slate-200">
              {ambulance.current_latitude !== null && ambulance.current_latitude !== undefined
                ? `${ambulance.current_latitude.toFixed(4)}° N, ${ambulance.current_longitude?.toFixed(4)}° E`
                : 'Awaiting Location Stream'}
            </span>
          </div>
          <Link
            to="/dashboard"
            className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-400 transition-colors"
            title="Return to Main Dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </div>
      </header>

      {/* Main Dispatch Active Dossier or Standby State */}
      <main className="flex-1 max-w-4xl mx-auto w-full">
        {activeDispatch ? (
          <div className="glass-card rounded-2xl p-6 md:p-8 border border-amber-500/40 bg-amber-950/10 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2 text-amber-400 font-mono font-bold text-sm">
                <AlertTriangle className="w-5 h-5" /> EMERGENCY DISPATCH ASSIGNED
              </div>
              <span className="px-3 py-1 rounded-lg bg-amber-500/20 text-amber-300 font-mono text-xs font-bold uppercase border border-amber-500/30">
                Dispatch Status: {activeDispatch.status}
              </span>
            </div>

            {/* Incident Details Card */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-slate-500 uppercase text-[10px]">Target Incident ID</span>
                <p className="font-bold text-cyan-300 text-sm">{activeDispatch.incident_id}</p>
                {activeDispatch.incident && (
                  <p className="text-slate-300">
                    Type: <strong className="uppercase text-amber-400">{activeDispatch.incident.incident_type}</strong> | Severity: <strong className="uppercase text-red-400">{activeDispatch.incident.severity || 'N/A'}</strong>
                  </p>
                )}
              </div>

              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-slate-500 uppercase text-[10px]">Incident Navigation Coordinates</span>
                <p className="font-bold text-rose-400 text-sm flex items-center gap-1.5">
                  <MapPin className="w-4 h-4" />
                  {activeDispatch.incident
                    ? `${activeDispatch.incident.latitude.toFixed(5)}° N, ${activeDispatch.incident.longitude.toFixed(5)}° E`
                    : 'Coordinates Pending'}
                </p>
                <p className="text-slate-400 text-[11px]">
                  Dispatched At: {new Date(activeDispatch.dispatched_at).toLocaleString()}
                </p>
              </div>
            </div>

            {/* Tablet Progression Buttons */}
            <div className="border-t border-slate-800 pt-6 space-y-3">
              <h3 className="font-bold text-sm text-slate-100 font-mono">Update Emergency Status:</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={() => handleUpdateStatus('en_route')}
                  disabled={activeDispatch.status !== 'dispatched' || updateStatusMutation.isPending}
                  className={`py-4 px-4 rounded-xl font-mono font-bold text-sm flex items-center justify-center gap-2 transition-all border ${
                    activeDispatch.status === 'en_route'
                      ? 'bg-amber-500 text-slate-950 border-amber-400 ring-2 ring-amber-400/50'
                      : activeDispatch.status === 'dispatched'
                      ? 'bg-amber-600/30 text-amber-300 border-amber-500/50 hover:bg-amber-600 hover:text-white'
                      : 'bg-slate-900 text-slate-600 border-slate-800 cursor-not-allowed opacity-50'
                  }`}
                >
                  <Navigation className="w-4 h-4" />
                  1. Mark En Route
                </button>

                <button
                  onClick={() => handleUpdateStatus('arrived')}
                  disabled={activeDispatch.status !== 'en_route' || updateStatusMutation.isPending}
                  className={`py-4 px-4 rounded-xl font-mono font-bold text-sm flex items-center justify-center gap-2 transition-all border ${
                    activeDispatch.status === 'arrived'
                      ? 'bg-rose-500 text-white border-rose-400 ring-2 ring-rose-400/50'
                      : activeDispatch.status === 'en_route'
                      ? 'bg-rose-600/30 text-rose-300 border-rose-500/50 hover:bg-rose-600 hover:text-white'
                      : 'bg-slate-900 text-slate-600 border-slate-800 cursor-not-allowed opacity-50'
                  }`}
                >
                  <MapPin className="w-4 h-4" />
                  2. Mark Arrived
                </button>

                <button
                  onClick={() => handleUpdateStatus('completed')}
                  disabled={activeDispatch.status !== 'arrived' || updateStatusMutation.isPending}
                  className={`py-4 px-4 rounded-xl font-mono font-bold text-sm flex items-center justify-center gap-2 transition-all border ${
                    activeDispatch.status === 'arrived'
                      ? 'bg-emerald-600 text-white border-emerald-500 hover:bg-emerald-500'
                      : 'bg-slate-900 text-slate-600 border-slate-800 cursor-not-allowed opacity-50'
                  }`}
                >
                  <CheckCircle className="w-4 h-4" />
                  3. Mark Completed
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="glass-card rounded-2xl p-12 border border-slate-800 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 mx-auto flex items-center justify-center text-emerald-400">
              <Shield className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold text-slate-100 font-mono">UNIT STANDING BY — AVAILABLE</h2>
            <p className="text-xs font-mono text-slate-400 max-w-md mx-auto">
              This vehicle is currently available and sending location telemetry over MQTT. New operator dispatch orders will appear here automatically.
            </p>
          </div>
        )}
      </main>
    </div>
  );
};
