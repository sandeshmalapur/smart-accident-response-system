import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api-client';
import { WelfareCheckResponse, WelfareCheckStatus } from '../lib/types';

export const useWelfareMessages = () => {
  return useQuery({
    queryKey: ['welfare-messages'],
    queryFn: () => api.getWelfareMessages(),
    staleTime: Infinity,
  });
};

export const useWelfareCheckByDevice = (deviceCode?: string) => {
  return useQuery({
    queryKey: ['welfare-check', 'device', deviceCode],
    queryFn: () => api.getWelfareCheckByDevice(deviceCode!),
    enabled: Boolean(deviceCode),
    refetchInterval: 3000,
    retry: false,
  });
};

export const useWelfareChecks = (params?: { incident_id?: string; device_id?: string; status?: WelfareCheckStatus }) => {
  return useQuery({
    queryKey: ['welfare-checks', params],
    queryFn: () => api.getWelfareChecks(params),
    refetchInterval: 3000,
  });
};

export const useRespondWelfareCheck = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ checkId, response }: { checkId: string; response: WelfareCheckResponse }) =>
      api.respondWelfareCheck(checkId, response),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['welfare-check'] });
      queryClient.invalidateQueries({ queryKey: ['welfare-checks'] });
    },
  });
};
