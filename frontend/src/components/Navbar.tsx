import React from 'react';
import { Activity, Radio, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

interface NavbarProps {
  isConnected: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ isConnected }) => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
          <Activity className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <h1 className="font-extrabold text-lg text-slate-100 tracking-tight flex items-center gap-2">
            SMART ACCIDENT RESPONSE
            <span className="text-[10px] font-mono font-normal px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 uppercase">
              v1.0 Operational
            </span>
          </h1>
          <p className="text-xs text-slate-400 font-mono">Real-time Telemetry & Anomaly Detection</p>
        </div>
      </div>

      {/* Connection & Profile */}
      <div className="flex items-center gap-4">
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border ${
            isConnected
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}
        >
          <Radio className={`w-3.5 h-3.5 ${isConnected ? 'animate-pulse' : ''}`} />
          <span>{isConnected ? 'LIVE FEED CONNECTED' : 'FEED DISCONNECTED'}</span>
        </div>

        {user && (
          <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                <UserIcon className="w-4 h-4" />
              </div>
              <div className="text-left hidden sm:block">
                <p className="text-xs font-bold text-slate-200">{user.full_name}</p>
                <p className="text-[10px] font-mono text-cyan-400 uppercase">{user.role}</p>
              </div>
            </div>

            <button
              onClick={logout}
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
