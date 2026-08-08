import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useIncidents } from '../hooks/useIncidents';
import { annotateIncidentCoOccurrence } from '../lib/incident-utils';
import { StatusBadge } from '../components/StatusBadge';
import { IncidentStatus, IncidentType } from '../lib/types';
import { Filter, ExternalLink, RefreshCw, AlertTriangle } from 'lucide-react';

export const IncidentsPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | ''>('');
  const [typeFilter, setTypeFilter] = useState<IncidentType | ''>('');

  const { data: rawIncidents = [], isLoading, refetch, isRefetching } = useIncidents({
    status: statusFilter || undefined,
    limit: 100,
  });

  // Apply the co-occurrence display rule on the full incident set first, then filter by incident_type for display
  const annotatedIncidents = useMemo(() => {
    const annotated = annotateIncidentCoOccurrence(rawIncidents);
    if (!typeFilter) return annotated;
    return annotated.filter((inc) => inc.incident_type === typeFilter);
  }, [rawIncidents, typeFilter]);

  return (
    <div className="space-y-6">
      {/* Header & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-extrabold text-slate-100 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-cyan-400" />
            Incident Audit Log
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">Historical incident management and triage</p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Status Filter */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs font-mono">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-900">All Statuses</option>
              <option value="open" className="bg-slate-900">Open</option>
              <option value="acknowledged" className="bg-slate-900">Acknowledged</option>
              <option value="resolved" className="bg-slate-900">Resolved</option>
              <option value="false_positive" className="bg-slate-900">False Positive</option>
            </select>
          </div>

          {/* Type Filter */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs font-mono">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as any)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-900">All Types</option>
              <option value="accident" className="bg-slate-900">Accident</option>
              <option value="gas_leak" className="bg-slate-900">Gas Leak</option>
            </select>
          </div>

          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/30 transition-colors"
            title="Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${isRefetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Incidents Data Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-cyan-400 font-mono text-sm">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
            Loading incidents database...
          </div>
        ) : annotatedIncidents.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">
            No incidents found matching the selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Incident Classification</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Device Reference</th>
                  <th className="px-4 py-3">Reading ID</th>
                  <th className="px-4 py-3">Coordinates</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {annotatedIncidents.map((inc) => (
                  <tr
                    key={inc.id}
                    className={`hover:bg-slate-900/50 transition-colors ${
                      inc.isCoOccurringGasLeak ? 'bg-slate-950/40 text-slate-400' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <StatusBadge variant={inc.badgeVariant} size="sm" />
                        </div>
                        <span className="font-bold text-slate-200 text-xs">{inc.displayTitle}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={inc.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 font-semibold text-cyan-400">{inc.device_id.substring(0, 13)}...</td>
                    <td className="px-4 py-3 text-slate-400">{inc.sensor_reading_id.substring(0, 13)}...</td>
                    <td className="px-4 py-3 text-slate-300">
                      {inc.latitude.toFixed(4)}, {inc.longitude.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {new Date(inc.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/incidents/${inc.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 text-cyan-400 border border-slate-700 hover:bg-cyan-500/20 transition-colors"
                      >
                        <span>Details</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
