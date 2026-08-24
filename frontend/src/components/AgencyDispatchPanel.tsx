import React from 'react';
import { ShieldAlert, Flame, Navigation, CheckCircle, XCircle, Phone } from 'lucide-react';
import { Incident, AgencyType, AgencyDispatchStatus } from '../lib/types';
import { useNearestAgencyUnits } from '../hooks/useAgencyUnits';
import { useAgencyDispatches, useCreateAgencyDispatch, useUpdateAgencyDispatchStatus } from '../hooks/useAgencyDispatches';

interface AgencyDispatchPanelProps {
  incident: Incident;
}

export const AgencyDispatchPanel: React.FC<AgencyDispatchPanelProps> = ({ incident }) => {
  const { data: nearestPolice = [], isLoading: loadingPolice } = useNearestAgencyUnits('police', incident.latitude, incident.longitude, 'available', 3);
  const { data: nearestFire = [], isLoading: loadingFire } = useNearestAgencyUnits('fire', incident.latitude, incident.longitude, 'available', 3);
  const { data: activeAgencyDispatches = [] } = useAgencyDispatches({ incident_id: incident.id });

  const createDispatchMutation = useCreateAgencyDispatch();
  const updateStatusMutation = useUpdateAgencyDispatchStatus();

  const handleDispatch = (agencyType: AgencyType, unitId: string) => {
    createDispatchMutation.mutate({
      incidentId: incident.id,
      agencyType,
      agencyUnitId: unitId,
    });
  };

  const handleStatusUpdate = (dispatchId: string, status: AgencyDispatchStatus) => {
    updateStatusMutation.mutate({ dispatchId, status });
  };

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 shadow-sm space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          Multi-Agency Triage & Dispatch
        </h3>
        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
          Incident ID: {incident.id.slice(0, 8)}
        </span>
      </div>

      {/* Active Agency Dispatches List */}
      {activeAgencyDispatches.length > 0 && (
        <div className="space-y-3 border-b border-gray-100 dark:border-gray-800 pb-5">
          <h4 className="text-xs uppercase tracking-wider font-semibold text-gray-500 dark:text-gray-400">
            Active Agency Response ({activeAgencyDispatches.length})
          </h4>
          <div className="space-y-2">
            {activeAgencyDispatches.map((disp) => {
              const isPolice = disp.agency_type === 'police';
              return (
                <div
                  key={disp.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/40"
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isPolice ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400' : 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-400'}`}>
                      {isPolice ? <ShieldAlert className="w-4 h-4" /> : <Flame className="w-4 h-4" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-gray-900 dark:text-gray-100">
                          {disp.agency_unit?.unit_code || 'Agency Unit'}
                        </span>
                        <span className="text-xs uppercase px-2 py-0.5 rounded font-semibold bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                          {disp.agency_type}
                        </span>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300">
                          {disp.status}
                        </span>
                      </div>
                      {disp.agency_unit?.contact_phone && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
                          <Phone className="w-3 h-3" />
                          {disp.agency_unit.contact_phone}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Status Transition Action Buttons */}
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {disp.status === 'pending' && (
                      <button
                        onClick={() => handleStatusUpdate(disp.id, 'en_route')}
                        disabled={updateStatusMutation.isPending}
                        className="px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white hover:bg-blue-700 transition"
                      >
                        En Route
                      </button>
                    )}
                    {(disp.status === 'pending' || disp.status === 'en_route') && (
                      <button
                        onClick={() => handleStatusUpdate(disp.id, 'on_scene')}
                        disabled={updateStatusMutation.isPending}
                        className="px-2.5 py-1 text-xs font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700 transition"
                      >
                        On Scene
                      </button>
                    )}
                    {disp.status !== 'completed' && disp.status !== 'cancelled' && (
                      <>
                        <button
                          onClick={() => handleStatusUpdate(disp.id, 'completed')}
                          disabled={updateStatusMutation.isPending}
                          className="px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition flex items-center gap-1"
                        >
                          <CheckCircle className="w-3 h-3" /> Complete
                        </button>
                        <button
                          onClick={() => handleStatusUpdate(disp.id, 'cancelled')}
                          disabled={updateStatusMutation.isPending}
                          className="px-2.5 py-1 text-xs font-semibold rounded-md bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-red-100 hover:text-red-700 transition flex items-center gap-1"
                        >
                          <XCircle className="w-3 h-3" /> Cancel
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Available Units Dispatch Panel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Police Column */}
        <div className="border border-gray-200 dark:border-gray-800 rounded-lg p-3.5 bg-blue-50/30 dark:bg-blue-950/10">
          <div className="flex items-center gap-2 mb-3">
            <ShieldAlert className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">Police Units</h4>
          </div>
          {loadingPolice ? (
            <div className="text-xs text-gray-500 py-2">Locating nearest police units...</div>
          ) : nearestPolice.length === 0 ? (
            <div className="text-xs text-gray-500 py-2">No available police units nearby</div>
          ) : (
            <div className="space-y-2">
              {nearestPolice.map((unit) => (
                <div key={unit.id} className="flex items-center justify-between p-2.5 rounded border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-xs">
                  <div>
                    <div className="font-bold text-gray-900 dark:text-gray-100">{unit.unit_code}</div>
                    <div className="text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
                      <Navigation className="w-3 h-3" />
                      {unit.distance_km.toFixed(2)} km away
                    </div>
                  </div>
                  <button
                    onClick={() => handleDispatch('police', unit.id)}
                    disabled={createDispatchMutation.isPending}
                    className="px-3 py-1.5 font-semibold rounded bg-blue-600 text-white hover:bg-blue-700 transition disabled:opacity-50"
                  >
                    Dispatch Police
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Fire Column */}
        <div className="border border-gray-200 dark:border-gray-800 rounded-lg p-3.5 bg-red-50/30 dark:bg-red-950/10">
          <div className="flex items-center gap-2 mb-3">
            <Flame className="w-4 h-4 text-red-600 dark:text-red-400" />
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">Fire Department Units</h4>
          </div>
          {loadingFire ? (
            <div className="text-xs text-gray-500 py-2">Locating nearest fire units...</div>
          ) : nearestFire.length === 0 ? (
            <div className="text-xs text-gray-500 py-2">No available fire units nearby</div>
          ) : (
            <div className="space-y-2">
              {nearestFire.map((unit) => (
                <div key={unit.id} className="flex items-center justify-between p-2.5 rounded border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-xs">
                  <div>
                    <div className="font-bold text-gray-900 dark:text-gray-100">{unit.unit_code}</div>
                    <div className="text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
                      <Navigation className="w-3 h-3" />
                      {unit.distance_km.toFixed(2)} km away
                    </div>
                  </div>
                  <button
                    onClick={() => handleDispatch('fire', unit.id)}
                    disabled={createDispatchMutation.isPending}
                    className="px-3 py-1.5 font-semibold rounded bg-red-600 text-white hover:bg-red-700 transition disabled:opacity-50"
                  >
                    Dispatch Fire
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
