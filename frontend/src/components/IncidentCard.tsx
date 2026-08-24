import React from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Clock, Cpu, ExternalLink, Activity } from 'lucide-react';
import { AnnotatedIncident } from '../lib/types';
import { StatusBadge } from './StatusBadge';
import { ResponseStatusBadge } from './ResponseStatusBadge';

interface IncidentCardProps {
  incident: AnnotatedIncident;
  onStatusChange?: (id: string, status: any) => void;
}

export const IncidentCard: React.FC<IncidentCardProps> = ({ incident }) => {
  const isCoOccurring = incident.isCoOccurringGasLeak;

  return (
    <div
      className={`glass-card glass-card-hover rounded-xl p-4 transition-all duration-200 ${
        isCoOccurring
          ? 'border-slate-800 bg-slate-900/60 opacity-80'
          : incident.badgeVariant === 'accident-severe'
          ? 'border-red-500/40 bg-red-950/20'
          : incident.badgeVariant === 'gas-critical'
          ? 'border-purple-500/40 bg-purple-950/20'
          : 'border-slate-800'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge variant={incident.badgeVariant} />
            <StatusBadge status={incident.status} size="sm" />
            <ResponseStatusBadge responseStatus={incident.response_status} compact />
            {isCoOccurring && (
              <span className="px-2 py-0.5 text-[10px] font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700 rounded">
                Secondary Anomaly
              </span>
            )}
          </div>
          <h3 className={`font-bold text-base mt-2 ${isCoOccurring ? 'text-slate-300 font-medium' : 'text-slate-100'}`}>
            {incident.displayTitle}
          </h3>
        </div>

        <Link
          to={`/incidents/${incident.id}`}
          className="p-2 rounded-lg bg-slate-800/80 hover:bg-cyan-500/20 text-slate-400 hover:text-cyan-300 border border-slate-700/60 transition-colors"
          title="View Incident Details"
        >
          <ExternalLink className="w-4 h-4" />
        </Link>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-xs font-mono text-slate-400 border-t border-slate-800/80 pt-3">
        <div className="flex items-center gap-1.5 truncate">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span className="truncate">{incident.device_id.substring(0, 13)}...</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>{new Date(incident.created_at).toLocaleTimeString()}</span>
        </div>
        <div className="flex items-center gap-1.5 col-span-2">
          <MapPin className="w-3.5 h-3.5 text-rose-400" />
          <span>
            GPS: {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
          </span>
        </div>
      </div>

      {(incident.severity_score !== undefined || incident.anomaly_score !== undefined) && (
        <div className="mt-3 flex items-center gap-4 text-xs font-mono bg-slate-950/50 px-3 py-1.5 rounded-md border border-slate-900">
          {incident.severity_score !== undefined && incident.severity_score !== null && (
            <div className="flex items-center gap-1">
              <Activity className="w-3 h-3 text-orange-400" />
              <span className="text-slate-400">SVM Conf:</span>
              <span className="font-bold text-slate-200">{(incident.severity_score * 100).toFixed(1)}%</span>
            </div>
          )}
          {incident.anomaly_score !== undefined && incident.anomaly_score !== null && (
            <div className="flex items-center gap-1">
              <Activity className="w-3 h-3 text-purple-400" />
              <span className="text-slate-400">GMM Score:</span>
              <span className="font-bold text-slate-200">{incident.anomaly_score.toFixed(2)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
