import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api-client';

export function useDevices(params?: { is_active?: boolean }) {
  return useQuery({
    queryKey: ['devices', params],
    queryFn: () => api.getDevices(params),
  });
}

export function useCreateDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      device_code: string;
      device_type: 'simulator' | 'esp32';
      label?: string;
      owner_name?: string;
      emergency_contact_name?: string;
      emergency_contact_phone?: string;
    }) => api.createDevice(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });
}

