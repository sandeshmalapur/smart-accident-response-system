import React, { useState } from 'react';
import { Truck, Plus, ShieldCheck, MapPin, ExternalLink, Radio } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAmbulances, useCreateAmbulance } from '../hooks/useAmbulances';
import { useAuth } from '../hooks/useAuth';

export const AmbulancesPage: React.FC = () => {
  const { user } = useAuth();
  const { data: ambulances = [], isLoading } = useAmbulances();
  const createAmbulanceMutation = useCreateAmbulance();

  const [showModal, setShowModal] = useState(false);
  const [ambulanceCode, setAmbulanceCode] = useState('');
  const [label, setLabel] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const isAdmin = user?.role === 'admin';

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!ambulanceCode.trim()) {
      setFormError('Ambulance code is required');
      return;
    }

    try {
      await createAmbulanceMutation.mutateAsync({
        ambulance_code: ambulanceCode.trim(),
        label: label.trim() || undefined,
      });
      setAmbulanceCode('');
      setLabel('');
      setShowModal(false);
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to register ambulance');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-extrabold text-slate-100 flex items-center gap-2">
            <Truck className="w-5 h-5 text-emerald-400" />
            Ambulance Fleet & Emergency Response Units
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Continuous location telemetry via MQTT & discrete operator-triggered dispatch status management
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all"
          >
            <Plus className="w-4 h-4" /> Register Ambulance
          </button>
        )}
      </div>

      {/* Ambulances Fleet Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-emerald-400 font-mono text-sm">Loading ambulance fleet status...</div>
        ) : ambulances.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">No ambulances registered in fleet database.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Unit Code</th>
                  <th className="px-4 py-3">Label / Call Sign</th>
                  <th className="px-4 py-3">Telemetry Coordinates</th>
                  <th className="px-4 py-3">Unit Status</th>
                  <th className="px-4 py-3">Last Location Update</th>
                  <th className="px-4 py-3 text-right">Tablet View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {ambulances.map((amb) => (
                  <tr key={amb.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-4 py-3 font-bold text-slate-200 flex items-center gap-2">
                      <Truck className="w-4 h-4 text-emerald-400" />
                      <span>{amb.ambulance_code}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{amb.label || <span className="text-slate-500 italic">No label</span>}</td>
                    <td className="px-4 py-3 text-cyan-400">
                      {amb.current_latitude !== null && amb.current_latitude !== undefined ? (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-slate-400" />
                          {amb.current_latitude.toFixed(4)}°, {amb.current_longitude?.toFixed(4)}°
                        </span>
                      ) : (
                        <span className="text-slate-500 italic">No telemetry yet</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                          amb.status === 'available'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : amb.status === 'dispatched' || amb.status === 'en_route'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse'
                            : amb.status === 'at_scene'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {amb.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {amb.last_location_update ? (
                        <span className="inline-flex items-center gap-1 text-[11px]">
                          <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
                          {new Date(amb.last_location_update).toLocaleTimeString()}
                        </span>
                      ) : (
                        <span className="text-slate-500 italic">Never</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/ambulance/${amb.ambulance_code}`}
                        className="inline-flex items-center gap-1 text-cyan-400 hover:underline font-bold text-xs"
                      >
                        Open Tablet <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Admin Register Ambulance Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Register New Emergency Ambulance (Admin)
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4 text-xs font-mono">
              <div className="space-y-1">
                <label className="text-slate-400 uppercase">Ambulance Code (Unique Identifier)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. AMB-001"
                  value={ambulanceCode}
                  onChange={(e) => setAmbulanceCode(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400 uppercase">Call Sign / Label (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Rapid Response Unit Alpha"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 border border-slate-800 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createAmbulanceMutation.isPending}
                  className="px-4 py-2 rounded-xl bg-emerald-500 text-white font-bold hover:bg-emerald-400"
                >
                  {createAmbulanceMutation.isPending ? 'Registering...' : 'Register Ambulance'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
