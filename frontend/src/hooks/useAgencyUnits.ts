import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api-client';
import { AgencyType, AgencyUnitStatus } from '../lib/types';

export function useAgencyUnits(params?: { agency_type?: AgencyType; status?: AgencyUnitStatus }) {
  return useQuery({
    queryKey: ['agency-units', params?.agency_type, params?.status],
    queryFn: () => api.getAgencyUnits(params),
    refetchInterval: 5000,
  });
}

export function useNearestAgencyUnits(
  agencyType: AgencyType,
  lat?: number,
  lng?: number,
  status: AgencyUnitStatus = 'available',
  limit: number = 3
) {
  return useQuery({
    queryKey: ['agency-units-nearest', agencyType, lat, lng, status, limit],
    queryFn: () => {
      if (lat === undefined || lng === undefined) return Promise.resolve([]);
      return api.getNearestAgencyUnits(agencyType, lat, lng, status, limit);
    },
    enabled: lat !== undefined && lng !== undefined,
    refetchInterval: 5000,
  });
}

export function useCreateAgencyUnit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      agency_type: AgencyType;
      unit_code: string;
      label?: string;
      contact_phone?: string;
      current_latitude?: number;
      current_longitude?: number;
    }) => api.createAgencyUnit(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agency-units'] });
    },
  });
}
