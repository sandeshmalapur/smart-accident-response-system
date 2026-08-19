import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api-client';
import { DispatchStatus } from '../lib/types';

export function useDispatches(params?: { incident_id?: string; ambulance_id?: string }) {
  return useQuery({
    queryKey: ['dispatches', params?.incident_id, params?.ambulance_id],
    queryFn: () => api.getDispatches(params),
    refetchInterval: 3000,
  });
}

export function useCreateDispatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ incidentId, ambulanceId }: { incidentId: string; ambulanceId: string }) =>
      api.createDispatch(incidentId, ambulanceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dispatches'] });
      queryClient.invalidateQueries({ queryKey: ['ambulances'] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useUpdateDispatchStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ dispatchId, status }: { dispatchId: string; status: DispatchStatus }) =>
      api.updateDispatchStatus(dispatchId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dispatches'] });
      queryClient.invalidateQueries({ queryKey: ['ambulances'] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}
