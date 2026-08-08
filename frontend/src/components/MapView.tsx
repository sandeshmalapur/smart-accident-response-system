import React from 'react';
import { MapPin, Navigation, Radio } from 'lucide-react';
import { SensorReading, Incident } from '../lib/types';

interface MapViewProps {
  readings: SensorReading[];
  incidents: Incident[];
}

export const MapView: React.FC<MapViewProps> = ({ readings, incidents }) => {
  const activeReading = readings[0];

  return (
    <div className="glass-card rounded-2xl p-5 border border-slate-800 relative overflow-hidden flex flex-col justify-between h-[360px]">
      {/* Background Radar Grid Pattern */}
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-40" />

      {/* Rotating Radar Line */}
      <div className="absolute top-1/2 left-1/2 w-[350px] h-[350px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-500/10 pointer-events-none">
        <div className="w-full h-full rounded-full border border-cyan-500/20" />
        <div className="absolute top-1/2 left-1/2 w-1/2 h-[2px] bg-gradient-to-r from-cyan-500/40 to-transparent origin-left animate-radar" />
      </div>

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Navigation className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-slate-100 uppercase tracking-wide">Live GPS Radar</h3>
            <p className="text-xs text-slate-400 font-mono">Real-time Telemetry Tracking</p>
          </div>
        </div>

        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-cyan-400">
          <Radio className="w-3 h-3 animate-pulse" />
          {readings.length} Active Feeds
        </span>
      </div>

      {/* Center GPS Radar Display */}
      <div className="relative z-10 my-auto text-center space-y-2 py-4">
        {activeReading ? (
          <div className="inline-block glass-card rounded-xl px-6 py-4 border border-cyan-500/30 glow-cyan">
            <div className="flex items-center justify-center gap-2 text-rose-400 font-mono text-lg font-bold">
              <MapPin className="w-5 h-5 animate-bounce" />
              <span>
                {activeReading.latitude.toFixed(5)}° N, {activeReading.longitude.toFixed(5)}° E
              </span>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-3 text-xs font-mono text-slate-400 border-t border-slate-800 pt-2">
              <div>
                <span className="block text-[10px] text-slate-500 uppercase">Accel Mag</span>
                <span className="font-semibold text-slate-200">
                  {Math.sqrt(
                    Math.pow(activeReading.accel_x, 2) +
                      Math.pow(activeReading.accel_y, 2) +
                      Math.pow(activeReading.accel_z, 2)
                  ).toFixed(2)}{' '}
                  g
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-slate-500 uppercase">Gas Level</span>
                <span className="font-semibold text-purple-300">{activeReading.gas_level.toFixed(0)} ppm</span>
              </div>
              <div>
                <span className="block text-[10px] text-slate-500 uppercase">Timestamp</span>
                <span className="font-semibold text-slate-300">
                  {new Date(activeReading.recorded_at).toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-slate-500 font-mono text-sm py-8">Awaiting telemetry coordinates from device...</div>
        )}
      </div>

      {/* Footer Incident Counter */}
      <div className="relative z-10 flex items-center justify-between text-xs font-mono text-slate-400 border-t border-slate-800/80 pt-3">
        <span>Active Incidents: {incidents.filter((i) => i.status === 'open').length}</span>
        <span className="text-cyan-400 hover:underline cursor-pointer">Open Fullscreen Map →</span>
      </div>
    </div>
  );
};
