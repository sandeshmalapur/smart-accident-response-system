import React from 'react';
import { Ambulance as AmbulanceIcon, ShieldAlert, Flame } from 'lucide-react';
import { IncidentResponseStatus, ResponderSummary } from '../lib/types';

interface ResponseStatusBadgeProps {
  responseStatus?: IncidentResponseStatus | null;
  compact?: boolean;
  className?: string;
}

export const ResponseStatusBadge: React.FC<ResponseStatusBadgeProps> = ({
  responseStatus,
  compact = false,
  className = '',
}) => {
  if (!responseStatus) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 ${className}`}>
        <span className="w-2 h-2 rounded-full bg-gray-400" />
        No Response
      </div>
    );
  }

  const getStatusColor = (responder: ResponderSummary | null) => {
    if (!responder) return 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500';
    const status = responder.status;
    if (status === 'completed') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400';
    if (status === 'cancelled') return 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500';
    return 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400 animate-pulse';
  };

  const getBadgeStyle = () => {
    switch (responseStatus.overall_status) {
      case 'resolved':
        return 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/30 dark:border-emerald-800 dark:text-emerald-300';
      case 'responding':
        return 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300';
      case 'no_response':
      default:
        return 'bg-gray-50 border-gray-200 text-gray-700 dark:bg-gray-800/50 dark:border-gray-700 dark:text-gray-400';
    }
  };

  const formatOverallText = (status: string) => {
    switch (status) {
      case 'resolved':
        return 'Resolved';
      case 'responding':
        return 'Responding';
      case 'no_response':
      default:
        return 'No Response';
    }
  };

  return (
    <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full border text-xs font-semibold ${getBadgeStyle()} ${className}`}>
      <div className="flex items-center gap-1">
        {/* Ambulance */}
        <span
          className={`p-1 rounded-full transition-colors ${getStatusColor(responseStatus.ambulance)}`}
          title={`Ambulance: ${responseStatus.ambulance?.status || 'None'}`}
        >
          <AmbulanceIcon className="w-3 h-3" />
        </span>

        {/* Police */}
        <span
          className={`p-1 rounded-full transition-colors ${getStatusColor(responseStatus.police)}`}
          title={`Police: ${responseStatus.police?.status || 'None'}`}
        >
          <ShieldAlert className="w-3 h-3" />
        </span>

        {/* Fire */}
        <span
          className={`p-1 rounded-full transition-colors ${getStatusColor(responseStatus.fire)}`}
          title={`Fire: ${responseStatus.fire?.status || 'None'}`}
        >
          <Flame className="w-3 h-3" />
        </span>
      </div>

      {!compact && (
        <span className="uppercase tracking-wider text-[10px] font-bold">
          {formatOverallText(responseStatus.overall_status)}
        </span>
      )}
    </div>
  );
};
