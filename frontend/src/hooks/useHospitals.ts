import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api-client';

export function useHospitals(params?: { is_active?: boolean }) {
  return useQuery({
    queryKey: ['hospitals', params],
    queryFn: () => api.getHospitals(params),
  });
}

export function useCreateHospital() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { name: string; latitude: number; longitude: number; phone?: string }) =>
      api.createHospital(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hospitals'] });
    },
  });
}

export function useNearestHospitals(lat: number | null, lng: number | null, limit: number = 3) {
  return useQuery({
    queryKey: ['hospitals', 'nearest', lat, lng, limit],
    queryFn: () => (lat !== null && lng !== null ? api.getNearestHospitals(lat, lng, limit) : Promise.resolve([])),
    enabled: lat !== null && lng !== null,
  });
}
