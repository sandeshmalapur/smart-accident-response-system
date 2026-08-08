import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api-client';
import { IncidentStatus } from '../lib/types';

export function useIncidents(params?: {
  status?: IncidentStatus;
  incident_type?: 'accident' | 'gas_leak';
  device_id?: string;
  sensor_reading_id?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['incidents', params],
    queryFn: () => api.getIncidents(params),
    refetchInterval: 5000, // Poll every 5s as fallback to WebSocket
  });
}

export function useIncident(id: string) {
  return useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.getIncident(id),
    enabled: Boolean(id),
  });
}

export function useUpdateIncidentStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: IncidentStatus }) =>
      api.updateIncidentStatus(id, status),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', updated.id] });
    },
  });
}
