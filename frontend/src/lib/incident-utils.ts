import { Incident, AnnotatedIncident } from './types';

/**
 * Pure utility function to annotate co-occurrence for incidents.
 *
 * Checks if a gas_leak incident shares a sensor_reading_id with an accident incident.
 * If so, marks it with `isCoOccurringGasLeak = true`, secondary muted badge variant,
 * and display title "Gas anomaly detected during accident".
 */
export function annotateIncidentCoOccurrence(incidents: Incident[]): AnnotatedIncident[] {
  // Collect set of sensor_reading_ids that triggered an accident
  const accidentReadingIds = new Set<string>();

  for (const inc of incidents) {
    if (inc.incident_type === 'accident' && inc.sensor_reading_id) {
      accidentReadingIds.add(inc.sensor_reading_id);
    }
  }

  return incidents.map((inc) => {
    if (inc.incident_type === 'gas_leak') {
      const hasSiblingAccident = Boolean(inc.sensor_reading_id && accidentReadingIds.has(inc.sensor_reading_id));

      if (hasSiblingAccident) {
        return {
          ...inc,
          isCoOccurringGasLeak: true,
          displayTitle: 'Gas anomaly detected during accident',
          badgeVariant: 'gas-secondary',
        };
      } else {
        return {
          ...inc,
          isCoOccurringGasLeak: false,
          displayTitle: 'Gas Leak Anomaly Detected',
          badgeVariant: 'gas-critical',
        };
      }
    }

    // Default formatting for accident type
    let badgeVariant: AnnotatedIncident['badgeVariant'] = 'accident-moderate';
    if (inc.severity === 'severe') badgeVariant = 'accident-severe';
    else if (inc.severity === 'minor') badgeVariant = 'accident-minor';

    const severityText = inc.severity ? `${inc.severity.toUpperCase()} ` : '';

    return {
      ...inc,
      isCoOccurringGasLeak: false,
      displayTitle: `${severityText}Vehicle Accident Detected`,
      badgeVariant,
    };
  });
}
