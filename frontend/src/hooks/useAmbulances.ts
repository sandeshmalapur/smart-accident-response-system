import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api-client';
import { AmbulanceStatus } from '../lib/types';

export function useAmbulances(status?: AmbulanceStatus) {
  return useQuery({
    queryKey: ['ambulances', status],
    queryFn: () => api.getAmbulances({ status }),
    refetchInterval: 3000,
  });
}

export function useNearestAmbulances(lat?: number, lng?: number, status: AmbulanceStatus = 'available', limit: number = 3) {
  return useQuery({
    queryKey: ['ambulances', 'nearest', lat, lng, status, limit],
    queryFn: () => (lat !== undefined && lng !== undefined ? api.getNearestAmbulances(lat, lng, status, limit) : []),
    enabled: lat !== undefined && lng !== undefined,
    refetchInterval: 3000,
  });
}

export function useAmbulance(identifier?: string) {
  return useQuery({
    queryKey: ['ambulance', identifier],
    queryFn: () => (identifier ? api.getAmbulance(identifier) : null),
    enabled: !!identifier,
    refetchInterval: 3000,
  });
}

export function useCreateAmbulance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { ambulance_code: string; label?: string }) => api.createAmbulance(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ambulances'] });
    },
  });
}
