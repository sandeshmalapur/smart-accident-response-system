import { useEffect, useState, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { SensorReading, Incident, Alert, WSMessage } from '../lib/types';

interface LiveFeedState {
  isConnected: boolean;
  latestReadings: Record<string, SensorReading>; // device_id -> SensorReading
  recentReadings: SensorReading[];
  liveIncidents: Incident[];
  liveAlerts: Alert[];
}

export function useLiveFeed(token: string | null) {
  const [state, setState] = useState<LiveFeedState>({
    isConnected: false,
    latestReadings: {},
    recentReadings: [],
    liveIncidents: [],
    liveAlerts: [],
  });

  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!token) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const defaultWsUrl = `${wsProtocol}//${window.location.host}/api/v1/ws/live`;
    const wsUrl = (import.meta.env && import.meta.env.VITE_WS_URL) || defaultWsUrl;
    const socket = new WebSocket(`${wsUrl}?token=${token}`);

    socket.onopen = () => {
      console.log('[WS] Connected to live telemetry feed');
      setState((prev) => ({ ...prev, isConnected: true }));
    };

    socket.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        console.log('[WS] Event received:', msg.type, msg.data);

        if (msg.type === 'reading') {
          const reading = msg.data;
          setState((prev) => {
            const updatedLatest = { ...prev.latestReadings, [reading.device_id]: reading };
            const updatedRecent = [reading, ...prev.recentReadings.slice(0, 49)];
            return {
              ...prev,
              latestReadings: updatedLatest,
              recentReadings: updatedRecent,
            };
          });
        } else if (msg.type === 'incident') {
          const incident = msg.data;
          setState((prev) => ({
            ...prev,
            liveIncidents: [incident, ...prev.liveIncidents.filter((i) => i.id !== incident.id).slice(0, 49)],
          }));
        } else if (msg.type === 'alert') {
          const alert = msg.data;
          setState((prev) => ({
            ...prev,
            liveAlerts: [alert, ...prev.liveAlerts.filter((a) => a.id !== alert.id).slice(0, 49)],
          }));
        } else if (msg.type === 'agency_dispatch') {
          queryClient.invalidateQueries({ queryKey: ['agency-dispatches'] });
          queryClient.invalidateQueries({ queryKey: ['agency-units'] });
          queryClient.invalidateQueries({ queryKey: ['incidents'] });
        } else if (msg.type === 'incident_response_status') {
          queryClient.invalidateQueries({ queryKey: ['incidents'] });
          queryClient.invalidateQueries({ queryKey: ['agency-dispatches'] });
          queryClient.invalidateQueries({ queryKey: ['dispatches'] });
        } else if (msg.type === 'dispatch') {
          const dispData = msg.data;
          queryClient.setQueriesData<any>({ queryKey: ['dispatches'] }, (old: any) => {
            if (!old) return [dispData];
            if (Array.isArray(old)) {
              const exists = old.some((d: any) => d.id === dispData.id);
              if (exists) {
                return old.map((d: any) => (d.id === dispData.id ? { ...d, ...dispData } : d));
              }
              return [dispData, ...old];
            }
            return old;
          });
          queryClient.invalidateQueries({ queryKey: ['dispatches'] });
          queryClient.invalidateQueries({ queryKey: ['ambulances'] });
          queryClient.invalidateQueries({ queryKey: ['incidents'] });
        } else if (msg.type === 'ambulance_location') {
          const ambData = msg.data;
          queryClient.setQueriesData<any>({ queryKey: ['ambulances'] }, (old: any) => {
            if (!old) return old;
            if (Array.isArray(old)) {
              return old.map((a: any) => (a.id === ambData.id ? { ...a, ...ambData } : a));
            }
            return old;
          });
          queryClient.invalidateQueries({ queryKey: ['ambulances'] });
          queryClient.invalidateQueries({ queryKey: ['dispatches'] });
        }
      } catch (err) {
        console.error('[WS] Failed to parse WebSocket message:', err);
      }
    };

    socket.onclose = (event) => {
      console.warn('[WS] Live feed disconnected', event.code, event.reason);
      setState((prev) => ({ ...prev, isConnected: false }));

      // Auto reconnect after 3 seconds if not intentionally closed
      if (event.code !== 1000) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      }
    };

    socket.onerror = (err) => {
      console.error('[WS] WebSocket error:', err);
    };

    wsRef.current = socket;
  }, [token, queryClient]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [connect]);

  return state;
}
