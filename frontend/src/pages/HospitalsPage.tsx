import React, { useState } from 'react';
import { Building2, Plus, CheckCircle2, XCircle, ShieldCheck, MapPin, Phone } from 'lucide-react';
import { useHospitals, useCreateHospital } from '../hooks/useHospitals';
import { useAuth } from '../hooks/useAuth';

export const HospitalsPage: React.FC = () => {
  const { user } = useAuth();
  const { data: hospitals = [], isLoading } = useHospitals();
  const createHospitalMutation = useCreateHospital();

  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [phone, setPhone] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const isAdmin = user?.role === 'admin';

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError('Hospital name is required');
      return;
    }

    const latNum = parseFloat(latitude);
    const lngNum = parseFloat(longitude);

    if (isNaN(latNum) || isNaN(lngNum)) {
      setFormError('Valid latitude and longitude numbers are required');
      return;
    }

    try {
      await createHospitalMutation.mutateAsync({
        name: name.trim(),
        latitude: latNum,
        longitude: lngNum,
        phone: phone.trim() || undefined,
      });
      setName('');
      setLatitude('');
      setLongitude('');
      setPhone('');
      setShowModal(false);
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to register hospital');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-extrabold text-slate-100 flex items-center gap-2">
            <Building2 className="w-5 h-5 text-emerald-400" />
            Hospital Directory & Medical Facilities
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Static hospital registry for auto-suggested nearest hospital emergency response
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all"
          >
            <Plus className="w-4 h-4" /> Register Hospital
          </button>
        )}
      </div>

      {/* Hospitals Directory Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-emerald-400 font-mono text-sm">Loading medical facilities...</div>
        ) : hospitals.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">No hospitals registered in the system.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Facility Name</th>
                  <th className="px-4 py-3">GPS Coordinates</th>
                  <th className="px-4 py-3">Emergency Contact</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created Date</th>
                  <th className="px-4 py-3 text-right">System ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {hospitals.map((hosp) => (
                  <tr key={hosp.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-4 py-3 font-bold text-slate-200 flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-emerald-400" />
                      <span>{hosp.name}</span>
                    </td>
                    <td className="px-4 py-3 text-cyan-400">
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        {hosp.latitude.toFixed(4)}°, {hosp.longitude.toFixed(4)}°
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {hosp.phone ? (
                        <span className="inline-flex items-center gap-1">
                          <Phone className="w-3 h-3 text-slate-500" />
                          {hosp.phone}
                        </span>
                      ) : (
                        <span className="text-slate-500 italic">No phone recorded</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {hosp.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> ACTIVE
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-slate-500 font-bold">
                          <XCircle className="w-3.5 h-3.5" /> INACTIVE
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400">{new Date(hosp.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{hosp.id.substring(0, 8)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Admin Register Hospital Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Register New Hospital (Admin)
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
                <label className="text-slate-400 uppercase">Hospital / Facility Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. City Emergency Trauma Care"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400 uppercase">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    required
                    placeholder="e.g. 12.9716"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 uppercase">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    required
                    placeholder="e.g. 77.5946"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-slate-400 uppercase">Emergency Phone (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. +91 80 2345 6789"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
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
                  disabled={createHospitalMutation.isPending}
                  className="px-4 py-2 rounded-xl bg-emerald-500 text-white font-bold hover:bg-emerald-400"
                >
                  {createHospitalMutation.isPending ? 'Registering...' : 'Register Hospital'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
