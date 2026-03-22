import { create } from "zustand";

const MAX_TRACKED_VEHICLES = 15000;
const MAX_METRIC_POINTS = 50;
const MAX_ALERTS = 100;
const METRIC_SNAPSHOT_INTERVAL_MS = 2500;

function timestampMs(value) {
  const parsed = Date.parse(value || "");
  return Number.isNaN(parsed) ? 0 : parsed;
}

function sortVehicles(vehiclesById) {
  return Object.values(vehiclesById)
    .sort((left, right) => timestampMs(right.timestamp) - timestampMs(left.timestamp))
    .map((vehicle) => vehicle.vehicle_id);
}

function trimVehicleMap(vehiclesById, orderedIds) {
  if (orderedIds.length <= MAX_TRACKED_VEHICLES) {
    return [vehiclesById, orderedIds];
  }
  const trimmedIds = orderedIds.slice(0, MAX_TRACKED_VEHICLES);
  const nextMap = {};
  trimmedIds.forEach((vehicleId) => {
    nextMap[vehicleId] = vehiclesById[vehicleId];
  });
  return [nextMap, trimmedIds];
}

function summarizeVehicles(orderedIds, vehiclesById) {
  if (orderedIds.length === 0) {
    return {
      averageHealth: 0,
      anomalies: 0,
      critical: 0,
    };
  }

  let healthTotal = 0;
  let anomalies = 0;
  let critical = 0;
  orderedIds.forEach((vehicleId) => {
    const vehicle = vehiclesById[vehicleId];
    if (!vehicle) {
      return;
    }
    healthTotal += Number(vehicle.health ?? vehicle.health_score ?? 0);
    if ((vehicle.status || vehicle.health_status) !== "healthy") {
      anomalies += 1;
    }
    if ((vehicle.status || vehicle.health_status) === "critical") {
      critical += 1;
    }
  });

  const averageHealth = healthTotal / orderedIds.length;
  return {
    averageHealth: Number(averageHealth.toFixed(1)),
    anomalies,
    critical,
  };
}

function nextMetricsHistory({ metricsHistory, lastMetricsSnapshotAt, timestamp, summary, force = false }) {
  const nextSnapshotAt = timestampMs(timestamp) || Date.now();
  if (!force && nextSnapshotAt - lastMetricsSnapshotAt < METRIC_SNAPSHOT_INTERVAL_MS) {
    return {
      metricsHistory,
      lastMetricsSnapshotAt,
    };
  }

  return {
    metricsHistory: [
      ...metricsHistory,
      {
        timestamp: timestamp || new Date(nextSnapshotAt).toISOString(),
        averageHealth: summary.averageHealth,
        anomalies: summary.anomalies,
        critical: summary.critical,
      },
    ].slice(-MAX_METRIC_POINTS),
    lastMetricsSnapshotAt: nextSnapshotAt,
  };
}

export const useFleetStore = create((set, get) => ({
  vehiclesById: {},
  orderedIds: [],
  visibleIds: [],
  alerts: [],
  metricsHistory: [],
  fleetSummary: {
    averageHealth: 0,
    anomalies: 0,
    critical: 0,
  },
  performanceMetrics: null,
  lastMetricsSnapshotAt: 0,
  selectedVehicleId: null,
  selectedVehicleDetails: null,
  systemStatus: null,
  wsConnected: false,
  loadingFleet: false,
  loadingVehicle: false,
  pageLimit: 200,
  pageOffset: 0,
  fleetSize: 0,
  filterText: "",
  statusFilter: "all",
  anomalyOnly: false,

  hydrateFleet(payload) {
    set((state) => ({
      ...(() => {
        const nextMap = { ...state.vehiclesById };
        payload.vehicles.forEach((vehicle) => {
          nextMap[vehicle.vehicle_id] = {
            ...nextMap[vehicle.vehicle_id],
            ...vehicle,
          };
        });

        const nextOrdered = sortVehicles(nextMap);
        const [trimmedMap, trimmedIds] = trimVehicleMap(nextMap, nextOrdered);
        const summary = summarizeVehicles(trimmedIds, trimmedMap);
        const metricState = nextMetricsHistory({
          metricsHistory: state.metricsHistory,
          lastMetricsSnapshotAt: state.lastMetricsSnapshotAt,
          timestamp: payload.timestamp,
          summary,
          force: state.metricsHistory.length === 0,
        });

        return {
          vehiclesById: trimmedMap,
          orderedIds: trimmedIds,
          visibleIds: state.visibleIds.filter((vehicleId) => trimmedMap[vehicleId]),
          fleetSize: Math.max(Number(payload.fleet_size || 0), state.fleetSize),
          selectedVehicleId: state.selectedVehicleId || trimmedIds[0] || null,
          fleetSummary: summary,
          ...metricState,
        };
      })(),
    }));
  },

  applyDelta(payload) {
    set((state) => {
      const nextMap = { ...state.vehiclesById };
      payload.vehicles?.forEach((vehicleDelta) => {
        const vehicleId = vehicleDelta.vehicle_id;
        nextMap[vehicleId] = {
          ...nextMap[vehicleId],
          vehicle_id: vehicleId,
          ...(vehicleDelta.changed_fields || {}),
        };
      });
      const nextOrdered = sortVehicles(nextMap);
      const [trimmedMap, trimmedIds] = trimVehicleMap(nextMap, nextOrdered);
      const visibleIds = state.visibleIds.filter((vehicleId) => trimmedMap[vehicleId]);
      const mergedAlerts = [...(payload.alerts || []), ...state.alerts]
        .filter((alert, index, collection) =>
          collection.findIndex((candidate) => candidate.vehicle_id === alert.vehicle_id) === index
        )
        .filter((alert) => {
          const currentVehicle = nextMap[alert.vehicle_id];
          return currentVehicle && (currentVehicle.status || currentVehicle.health_status) !== "healthy";
        })
        .slice(0, MAX_ALERTS);
      const summary = summarizeVehicles(trimmedIds, trimmedMap);
      const metricState = nextMetricsHistory({
        metricsHistory: state.metricsHistory,
        lastMetricsSnapshotAt: state.lastMetricsSnapshotAt,
        timestamp: payload.timestamp,
        summary,
      });
      const selectedVehicleDetails =
        state.selectedVehicleId && trimmedMap[state.selectedVehicleId] && state.selectedVehicleDetails?.latest
          ? {
              ...state.selectedVehicleDetails,
              latest: {
                ...state.selectedVehicleDetails.latest,
                ...trimmedMap[state.selectedVehicleId],
              },
            }
          : state.selectedVehicleDetails;

      return {
        vehiclesById: trimmedMap,
        orderedIds: trimmedIds,
        visibleIds,
        alerts: mergedAlerts,
        fleetSize: Math.max(Number(payload.fleet_size || 0), state.fleetSize),
        fleetSummary: summary,
        selectedVehicleDetails,
        ...metricState,
      };
    });
  },

  setVisibleIds(visibleIds) {
    set({ visibleIds });
  },

  setSelectedVehicle(vehicleId) {
    set({ selectedVehicleId: vehicleId });
  },

  setSelectedVehicleDetails(details) {
    set({ selectedVehicleDetails: details });
  },

  setSystemStatus(systemStatus) {
    set({ systemStatus });
  },

  setPerformanceMetrics(performanceMetrics) {
    set({ performanceMetrics });
  },

  setAlerts(alerts) {
    set({ alerts: alerts.slice(0, MAX_ALERTS) });
  },

  setWsConnected(wsConnected) {
    set({ wsConnected });
  },

  setLoadingFleet(loadingFleet) {
    set({ loadingFleet });
  },

  setLoadingVehicle(loadingVehicle) {
    set({ loadingVehicle });
  },

  setFilterText(filterText) {
    set({ filterText });
  },

  setStatusFilter(statusFilter) {
    set({ statusFilter });
  },

  setAnomalyOnly(anomalyOnly) {
    set({ anomalyOnly });
  },

  setPageOffset(pageOffset) {
    set({ pageOffset: Math.max(0, pageOffset) });
  },

  nextPage() {
    const { pageLimit, pageOffset, fleetSize } = get();
    const nextOffset = pageOffset + pageLimit;
    if (nextOffset < fleetSize) {
      set({ pageOffset: nextOffset });
    }
  },

  previousPage() {
    const { pageLimit, pageOffset } = get();
    set({ pageOffset: Math.max(0, pageOffset - pageLimit) });
  },
}));
