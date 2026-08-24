import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api-client';
import { AgencyDispatchStatus, AgencyType } from '../lib/types';

export function useAgencyDispatches(params?: { incident_id?: string; agency_unit_id?: string; agency_type?: AgencyType }) {
  return useQuery({
    queryKey: ['agency-dispatches', params?.incident_id, params?.agency_unit_id, params?.agency_type],
    queryFn: () => api.getAgencyDispatches(params),
    refetchInterval: 3000,
  });
}

export function useCreateAgencyDispatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ incidentId, agencyType, agencyUnitId }: { incidentId: string; agencyType: AgencyType; agencyUnitId: string }) =>
      api.createAgencyDispatch(incidentId, { agency_type: agencyType, agency_unit_id: agencyUnitId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agency-dispatches'] });
      queryClient.invalidateQueries({ queryKey: ['agency-units'] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useUpdateAgencyDispatchStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ dispatchId, status }: { dispatchId: string; status: AgencyDispatchStatus }) =>
      api.updateAgencyDispatchStatus(dispatchId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agency-dispatches'] });
      queryClient.invalidateQueries({ queryKey: ['agency-units'] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}
