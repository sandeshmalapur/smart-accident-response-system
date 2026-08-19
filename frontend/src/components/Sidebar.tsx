import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, AlertCircle, Cpu, Building2, Truck } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/dashboard', label: 'Live Operations', icon: LayoutDashboard },
    { to: '/incidents', label: 'Incident Records', icon: AlertCircle },
    { to: '/hospitals', label: 'Hospitals Directory', icon: Building2 },
    { to: '/ambulances', label: 'Ambulance Fleet', icon: Truck },
    { to: '/devices', label: 'Hardware & Simulators', icon: Cpu },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950/60 flex flex-col justify-between p-4 sticky top-16 h-[calc(100vh-4rem)]">
      <nav className="space-y-1.5">
        <div className="px-3 py-2 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500">
          Command Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-150 ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-md shadow-cyan-500/10 font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="glass-card rounded-xl p-3.5 text-xs font-mono space-y-1.5 border border-slate-800/80">
        <p className="text-slate-400 font-semibold flex items-center justify-between">
          <span>Backend Target:</span>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
        </p>
        <p className="text-[11px] text-cyan-400 truncate">http://localhost:8000</p>
        <p className="text-[10px] text-slate-500">FastAPI + Supabase DB</p>
      </div>
    </aside>
  );
};
