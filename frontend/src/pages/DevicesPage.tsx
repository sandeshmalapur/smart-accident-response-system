import React, { useState } from 'react';
import { useDevices, useCreateDevice } from '../hooks/useDevices';
import { useAuth } from '../hooks/useAuth';
import { Cpu, Plus, CheckCircle2, XCircle, ShieldCheck } from 'lucide-react';

export const DevicesPage: React.FC = () => {
  const { data: devices = [], isLoading } = useDevices();
  const createDeviceMutation = useCreateDevice();
  const { user } = useAuth();

  const [deviceCode, setDeviceCode] = useState('');
  const [deviceType, setDeviceType] = useState<'simulator' | 'esp32'>('simulator');
  const [label, setLabel] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const isAdmin = user?.role === 'admin';

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!deviceCode.trim()) {
      setFormError('Device code is required');
      return;
    }

    try {
      await createDeviceMutation.mutateAsync({
        device_code: deviceCode.trim(),
        device_type: deviceType,
        label: label.trim() || undefined,
      });
      setDeviceCode('');
      setLabel('');
      setShowModal(false);
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to register device');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-extrabold text-slate-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-cyan-400" />
            Registered Devices & Hardware Nodes
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">ESP32 edge nodes and sensor simulation instances</p>
        </div>

        {isAdmin && (
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs shadow-lg shadow-cyan-500/20 transition-all"
          >
            <Plus className="w-4 h-4" /> Register New Device
          </button>
        )}
      </div>

      {/* Devices List Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-cyan-400 font-mono text-sm">Loading registered devices...</div>
        ) : devices.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">No devices registered in the system.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Device Code</th>
                  <th className="px-4 py-3">Hardware Type</th>
                  <th className="px-4 py-3">Label / Description</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Registration Date</th>
                  <th className="px-4 py-3 text-right">System UUID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {devices.map((dev) => (
                  <tr key={dev.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-4 py-3 font-bold text-cyan-400 flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-slate-500" />
                      <span>{dev.device_code}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-slate-800 text-slate-300 border border-slate-700">
                        {dev.device_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{dev.label || 'Unlabeled Node'}</td>
                    <td className="px-4 py-3">
                      {dev.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> ACTIVE
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-slate-500 font-bold">
                          <XCircle className="w-3.5 h-3.5" /> INACTIVE
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400">{new Date(dev.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{dev.id.substring(0, 8)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Admin Register Device Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
                Register New Sensor Node (Admin)
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
                <label className="text-slate-400 uppercase">Device Code (Unique)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. SIM-002 or ESP32-005"
                  value={deviceCode}
                  onChange={(e) => setDeviceCode(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400 uppercase">Device Type</label>
                <select
                  value={deviceType}
                  onChange={(e) => setDeviceType(e.target.value as any)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                >
                  <option value="simulator">Simulator</option>
                  <option value="esp32">ESP32 Hardware</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-400 uppercase">Label (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Fleet Vehicle Alpha"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
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
                  disabled={createDeviceMutation.isPending}
                  className="px-4 py-2 rounded-xl bg-cyan-500 text-white font-bold hover:bg-cyan-400"
                >
                  {createDeviceMutation.isPending ? 'Registering...' : 'Register Device'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
