import { describe, it, expect } from 'vitest';
import { annotateIncidentCoOccurrence } from './incident-utils';
import { Incident } from './types';

describe('annotateIncidentCoOccurrence', () => {
  it('annotates gas_leak WITH sibling accident on same sensor_reading_id as co-occurring', () => {
    const readingId = 'sr-12345';
    const mockIncidents: Incident[] = [
      {
        id: 'inc-1',
        device_id: 'dev-1',
        sensor_reading_id: readingId,
        incident_type: 'accident',
        severity: 'severe',
        severity_score: 0.95,
        latitude: 12.97,
        longitude: 77.59,
        status: 'open',
        created_at: new Date().toISOString(),
      },
      {
        id: 'inc-2',
        device_id: 'dev-1',
        sensor_reading_id: readingId,
        incident_type: 'gas_leak',
        anomaly_score: 0.88,
        latitude: 12.97,
        longitude: 77.59,
        status: 'open',
        created_at: new Date().toISOString(),
      },
    ];

    const result = annotateIncidentCoOccurrence(mockIncidents);

    const gasLeakAnnotated = result.find((i) => i.id === 'inc-2');
    expect(gasLeakAnnotated).toBeDefined();
    expect(gasLeakAnnotated?.isCoOccurringGasLeak).toBe(true);
    expect(gasLeakAnnotated?.displayTitle).toBe('Gas anomaly detected during accident');
    expect(gasLeakAnnotated?.badgeVariant).toBe('gas-secondary');
  });

  it('annotates standalone gas_leak WITHOUT sibling accident as standalone critical', () => {
    const mockIncidents: Incident[] = [
      {
        id: 'inc-3',
        device_id: 'dev-2',
        sensor_reading_id: 'sr-99999',
        incident_type: 'gas_leak',
        anomaly_score: 0.92,
        latitude: 13.01,
        longitude: 77.62,
        status: 'open',
        created_at: new Date().toISOString(),
      },
    ];

    const result = annotateIncidentCoOccurrence(mockIncidents);

    const gasLeakAnnotated = result[0];
    expect(gasLeakAnnotated.isCoOccurringGasLeak).toBe(false);
    expect(gasLeakAnnotated.displayTitle).toBe('Gas Leak Anomaly Detected');
    expect(gasLeakAnnotated.badgeVariant).toBe('gas-critical');
  });
});
