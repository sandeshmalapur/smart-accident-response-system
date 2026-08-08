import React from 'react';
import { clsx } from 'clsx';
import { ShieldAlert, Flame, AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { AnnotatedIncident, IncidentStatus } from '../lib/types';

interface StatusBadgeProps {
  variant?: AnnotatedIncident['badgeVariant'];
  status?: IncidentStatus;
  customText?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ variant, status, customText, size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs font-semibold rounded-md gap-1',
    md: 'px-2.5 py-1 text-xs font-bold rounded-lg gap-1.5',
    lg: 'px-3 py-1.5 text-sm font-extrabold rounded-lg gap-2',
  }[size];

  if (status) {
    const statusStyles: Record<IncidentStatus, { bg: string; icon: any; label: string }> = {
      open: { bg: 'bg-red-500/10 text-red-400 border border-red-500/30', icon: AlertTriangle, label: 'OPEN' },
      acknowledged: { bg: 'bg-amber-500/10 text-amber-400 border border-amber-500/30', icon: Info, label: 'ACKNOWLEDGED' },
      resolved: { bg: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30', icon: CheckCircle2, label: 'RESOLVED' },
      false_positive: { bg: 'bg-slate-500/10 text-slate-400 border border-slate-500/30', icon: Info, label: 'FALSE POSITIVE' },
    };

    const style = statusStyles[status];
    const Icon = style.icon;

    return (
      <span className={clsx('inline-flex items-center tracking-wider uppercase', sizeClasses, style.bg)}>
        <Icon className="w-3.5 h-3.5" />
        {customText || style.label}
      </span>
    );
  }

  if (variant) {
    const variantStyles: Record<AnnotatedIncident['badgeVariant'], { bg: string; icon: any; label: string }> = {
      'accident-severe': {
        bg: 'bg-red-500/20 text-red-400 border border-red-500/50 glow-red animate-pulse-glow',
        icon: ShieldAlert,
        label: 'SEVERE CRASH',
      },
      'accident-moderate': {
        bg: 'bg-orange-500/20 text-orange-400 border border-orange-500/40 glow-amber',
        icon: ShieldAlert,
        label: 'MODERATE ACCIDENT',
      },
      'accident-minor': {
        bg: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
        icon: AlertTriangle,
        label: 'MINOR ACCIDENT',
      },
      'gas-critical': {
        bg: 'bg-purple-500/20 text-purple-300 border border-purple-500/50 glow-cyan animate-pulse-glow',
        icon: Flame,
        label: 'CRITICAL GAS LEAK',
      },
      'gas-secondary': {
        bg: 'bg-slate-800/80 text-slate-400 border border-slate-700/60',
        icon: Info,
        label: 'GAS ANOMALY (CO-OCCURRING)',
      },
    };

    const style = variantStyles[variant];
    const Icon = style.icon;

    return (
      <span className={clsx('inline-flex items-center tracking-wider uppercase', sizeClasses, style.bg)}>
        <Icon className="w-3.5 h-3.5" />
        {customText || style.label}
      </span>
    );
  }

  return null;
};
