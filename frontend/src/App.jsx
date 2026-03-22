import { startTransition, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import AlertPanel from "./components/AlertPanel.jsx";
import AppHeader from "./components/AppHeader.jsx";
import FleetMap from "./components/FleetMap.jsx";
import FooterBar from "./components/FooterBar.jsx";
import VehicleDetailPanel from "./components/VehicleDetailPanel.jsx";
import VehicleTable from "./components/VehicleTable.jsx";
import { getAlerts, getFleet, getSystemStatus, getVehicle, postClientMetrics } from "./services/api";
import { connectFleetSocket } from "./services/socket";
import { useFleetStore } from "./store/useFleetStore";

const FLEET_FETCH_LIMIT = 20000;
const PAGE_SIZE = 200;
const MAP_MARKER_LIMIT = 200;
const SOCKET_FLUSH_INTERVAL_MS = 120;
const CLIENT_METRIC_INTERVAL_MS = 5000;
const SOCKET_INITIAL_RECONNECT_DELAY_MS = 1000;
const SOCKET_MAX_RECONNECT_DELAY_MS = 30000;
const SOCKET_MAX_RECONNECT_ATTEMPTS = 10;

function vehicleListFromState(orderedIds, vehiclesById) {
  return orderedIds.map((vehicleId) => vehiclesById[vehicleId]).filter(Boolean);
}

function mergeAlerts(currentAlerts = [], nextAlerts = []) {
  const dedupedAlerts = new Map();
  [...nextAlerts, ...currentAlerts].forEach((alert) => {
    const key = alert.vehicle_id || alert.alert_id;
    if (!key || dedupedAlerts.has(key)) {
      return;
    }
    dedupedAlerts.set(key, alert);
  });
  return Array.from(dedupedAlerts.values()).slice(0, 100);
}

function mergeSocketPayloads(currentPayload, nextPayload) {
  const normalizeVehicleUpdate = (vehicleUpdate) => {
    const { vehicle_id, timestamp, changed_fields, ...rest } = vehicleUpdate;
    return {
      vehicle_id,
      timestamp,
      changed_fields: changed_fields || rest,
    };
  };

  const basePayload = currentPayload || {
    type: nextPayload.type || "delta_batch",
    timestamp: nextPayload.timestamp,
    fleet_size: nextPayload.fleet_size,
    lag_ms: Number(nextPayload.lag_ms || 0),
    alerts: [],
    vehicles: [],
  };

  const vehicleMap = new Map((basePayload.vehicles || []).map((vehicle) => [vehicle.vehicle_id, normalizeVehicleUpdate(vehicle)]));
  (nextPayload.vehicles || []).forEach((vehicleUpdate) => {
    const normalizedUpdate = normalizeVehicleUpdate(vehicleUpdate);
    const existing = vehicleMap.get(normalizedUpdate.vehicle_id);
    if (!existing) {
      vehicleMap.set(normalizedUpdate.vehicle_id, normalizedUpdate);
      return;
    }

    vehicleMap.set(normalizedUpdate.vehicle_id, {
      vehicle_id: normalizedUpdate.vehicle_id,
      timestamp: normalizedUpdate.timestamp || existing.timestamp,
      changed_fields: {
        ...(existing.changed_fields || {}),
        ...(normalizedUpdate.changed_fields || {}),
      },
    });
  });

  return {
    type: "delta_batch",
    timestamp: nextPayload.timestamp || basePayload.timestamp,
    fleet_size: nextPayload.fleet_size || basePayload.fleet_size,
    lag_ms: Math.max(Number(basePayload.lag_ms || 0), Number(nextPayload.lag_ms || 0)),
    alerts: mergeAlerts(basePayload.alerts, nextPayload.alerts),
    vehicles: Array.from(vehicleMap.values()),
  };
}

function estimateClientLag(payload) {
  const timestamp = Date.parse(payload?.timestamp || "");
  if (Number.isNaN(timestamp)) {
    return Number(payload?.lag_ms || 0);
  }
  return Math.max(Number(payload?.lag_ms || 0), Date.now() - timestamp);
}

function socketStatusLabel(status, retryCount) {
  switch (status) {
    case "open":
      return "Live Data";
    case "reconnecting":
      return retryCount > 0 ? `Reconnecting (${retryCount})` : "Reconnecting";
    case "failed":
      return "Stream Offline";
    case "closed":
      return "Disconnected";
    default:
      return "Connecting";
  }
}

export default function App() {
  const vehiclesById = useFleetStore((state) => state.vehiclesById);
  const orderedIds = useFleetStore((state) => state.orderedIds);
  const alerts = useFleetStore((state) => state.alerts);
  const fleetSummary = useFleetStore((state) => state.fleetSummary);
  const selectedVehicleId = useFleetStore((state) => state.selectedVehicleId);
  const selectedVehicleDetails = useFleetStore((state) => state.selectedVehicleDetails);
  const systemStatus = useFleetStore((state) => state.systemStatus);
  const wsConnected = useFleetStore((state) => state.wsConnected);
  const loadingFleet = useFleetStore((state) => state.loadingFleet);
  const loadingVehicle = useFleetStore((state) => state.loadingVehicle);
  const filterText = useFleetStore((state) => state.filterText);
  const statusFilter = useFleetStore((state) => state.statusFilter);

  const hydrateFleet = useFleetStore((state) => state.hydrateFleet);
  const applyDelta = useFleetStore((state) => state.applyDelta);
  const setSelectedVehicle = useFleetStore((state) => state.setSelectedVehicle);
  const setSelectedVehicleDetails = useFleetStore((state) => state.setSelectedVehicleDetails);
  const setSystemStatus = useFleetStore((state) => state.setSystemStatus);
  const setAlerts = useFleetStore((state) => state.setAlerts);
  const setWsConnected = useFleetStore((state) => state.setWsConnected);
  const setLoadingFleet = useFleetStore((state) => state.setLoadingFleet);
  const setLoadingVehicle = useFleetStore((state) => state.setLoadingVehicle);
  const setFilterText = useFleetStore((state) => state.setFilterText);
  const setStatusFilter = useFleetStore((state) => state.setStatusFilter);

  const [pageIndex, setPageIndex] = useState(0);
  const [socketState, setSocketState] = useState({ status: "connecting", retryCount: 0 });
  const pendingSocketPayloadRef = useRef(null);
  const socketFlushTimerRef = useRef(null);
  const lastClientMetricsAtRef = useRef(0);

  const allVehicles = useMemo(() => vehicleListFromState(orderedIds, vehiclesById), [orderedIds, vehiclesById]);
  const deferredFilterText = useDeferredValue(filterText.trim().toLowerCase());
  const filteredVehicles = useMemo(
    () =>
      allVehicles.filter((vehicle) => {
        if (deferredFilterText) {
          const haystack = `${vehicle.vehicle_id} ${vehicle.model || ""}`.toLowerCase();
          if (!haystack.includes(deferredFilterText)) {
            return false;
          }
        }

        if (statusFilter !== "all" && vehicle.status !== statusFilter) {
          return false;
        }

        return true;
      }),
    [allVehicles, deferredFilterText, statusFilter],
  );
  const totalPages = Math.max(1, Math.ceil(filteredVehicles.length / PAGE_SIZE));
  const currentPageIndex = Math.min(pageIndex, Math.max(0, totalPages - 1));
  const pagedVehicles = useMemo(() => {
    const pageOffset = currentPageIndex * PAGE_SIZE;
    return filteredVehicles.slice(pageOffset, pageOffset + PAGE_SIZE);
  }, [currentPageIndex, filteredVehicles]);
  const deferredMapVehicles = useDeferredValue(pagedVehicles.slice(0, MAP_MARKER_LIMIT));
  const searchNotFound = Boolean(filterText.trim()) && filteredVehicles.length === 0;
  const pageStart = filteredVehicles.length === 0 ? 0 : currentPageIndex * PAGE_SIZE + 1;
  const pageEnd = Math.min((currentPageIndex + 1) * PAGE_SIZE, filteredVehicles.length);
  const wsStatusLabel = useMemo(
    () => socketStatusLabel(socketState.status, socketState.retryCount),
    [socketState.retryCount, socketState.status],
  );
  const systemHealthy = (systemStatus?.redis || "healthy") === "healthy" &&
    (systemStatus?.postgres || "healthy") === "healthy";

  const handleVehicleSelect = useCallback((vehicleId) => {
    setSelectedVehicle(vehicleId);
  }, [setSelectedVehicle]);

  const flushSocketPayload = useCallback(() => {
    socketFlushTimerRef.current = null;
    const payload = pendingSocketPayloadRef.current;
    pendingSocketPayloadRef.current = null;
    if (!payload) {
      return;
    }

    const renderStart = performance.now();
    const lagMs = estimateClientLag(payload);
    startTransition(() => applyDelta(payload));

    if (Date.now() - lastClientMetricsAtRef.current >= CLIENT_METRIC_INTERVAL_MS) {
      lastClientMetricsAtRef.current = Date.now();
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          postClientMetrics({
            render_time: performance.now() - renderStart,
            lag_ms: lagMs,
          }).catch(() => {});
        });
      });
    }
  }, [applyDelta]);

  useEffect(() => {
    setPageIndex(0);
  }, [deferredFilterText, statusFilter]);

  useEffect(() => {
    if (pagedVehicles.length === 0) {
      setSelectedVehicle(null);
      setSelectedVehicleDetails(null);
      return;
    }

    const selectedStillVisible = pagedVehicles.some((vehicle) => vehicle.vehicle_id === selectedVehicleId);
    if (!selectedStillVisible) {
      setSelectedVehicle(pagedVehicles[0].vehicle_id);
    }
  }, [pagedVehicles, selectedVehicleId, setSelectedVehicle, setSelectedVehicleDetails]);

  useEffect(() => {
    let active = true;
    const loadFleet = async () => {
      setLoadingFleet(true);
      try {
        const payload = await getFleet(FLEET_FETCH_LIMIT, 0);
        if (!active) {
          return;
        }
        startTransition(() => hydrateFleet(payload));
      } catch (error) {
        console.error("Failed to load fleet snapshot", error);
      } finally {
        if (active) {
          setLoadingFleet(false);
        }
      }
    };

    loadFleet();
    return () => {
      active = false;
    };
  }, [hydrateFleet, setLoadingFleet]);

  useEffect(() => {
    let active = true;
    const loadStatus = async () => {
      try {
        const [statusPayload, alertPayload] = await Promise.all([
          getSystemStatus(),
          getAlerts(25),
        ]);
        if (!active) {
          return;
        }
        setSystemStatus(statusPayload);
        setAlerts(alertPayload.alerts || []);
      } catch (error) {
        console.error("Failed to refresh system status", error);
      }
    };

    loadStatus();
    const intervalId = window.setInterval(loadStatus, 5000);
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [setAlerts, setSystemStatus]);

  useEffect(() => {
    if (!selectedVehicleId) {
      return undefined;
    }
    let active = true;
    const loadVehicle = async () => {
      setLoadingVehicle(true);
      try {
        const payload = await getVehicle(selectedVehicleId);
        if (active) {
          setSelectedVehicleDetails(payload);
        }
      } catch (error) {
        console.error("Failed to load vehicle details", error);
        if (active) {
          setSelectedVehicleDetails(null);
        }
      } finally {
        if (active) {
          setLoadingVehicle(false);
        }
      }
    };

    loadVehicle();
    const intervalId = window.setInterval(loadVehicle, 6000);
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [selectedVehicleId, setLoadingVehicle, setSelectedVehicleDetails]);

  useEffect(() => {
    let disposed = false;
    const clearSocketFlush = () => {
      if (socketFlushTimerRef.current !== null) {
        window.clearTimeout(socketFlushTimerRef.current);
        socketFlushTimerRef.current = null;
      }
      pendingSocketPayloadRef.current = null;
    };

    const refreshFleetSnapshot = async () => {
      try {
        const payload = await getFleet(FLEET_FETCH_LIMIT, 0);
        if (!disposed) {
          startTransition(() => hydrateFleet(payload));
        }
      } catch (error) {
        console.error("Failed to refresh fleet snapshot after reconnect", error);
      }
    };

    const fallbackInterval = window.setInterval(() => {
      if (!disposed) {
        void refreshFleetSnapshot();
      }
    }, 10000);

    const socketClient = connectFleetSocket(
      {
        onStateChange: ({ status, retryCount }) => {
          if (disposed) {
            return;
          }
          setSocketState({ status, retryCount });
          setWsConnected(status === "open");
        },
        onOpen: ({ wasReconnect }) => {
          if (disposed || !wasReconnect) {
            return;
          }
          void refreshFleetSnapshot();
        },
        onClose: () => {
          if (!disposed) {
            clearSocketFlush();
          }
        },
        onMessage: (payload) => {
          if (payload.type === "connected") {
            return;
          }
          (payload.vehicles || []).forEach((vehicle) => {
            const rul = vehicle.rul ?? vehicle.changed_fields?.rul;
            if (rul !== undefined) {
              console.log("RUL:", rul);
            }
          });
          pendingSocketPayloadRef.current = mergeSocketPayloads(pendingSocketPayloadRef.current, payload);
          if (socketFlushTimerRef.current === null) {
            socketFlushTimerRef.current = window.setTimeout(flushSocketPayload, SOCKET_FLUSH_INTERVAL_MS);
          }
        },
        onError: (error) => {
          if (!disposed) {
            console.error("Fleet WebSocket error", error);
          }
        },
        onReconnectStop: (details) => {
          if (!disposed) {
            console.error("Fleet WebSocket retries exhausted", details);
          }
        },
      },
      {
        initialReconnectDelayMs: SOCKET_INITIAL_RECONNECT_DELAY_MS,
        maxReconnectDelayMs: SOCKET_MAX_RECONNECT_DELAY_MS,
        maxReconnectAttempts: SOCKET_MAX_RECONNECT_ATTEMPTS,
      },
    );

    return () => {
      disposed = true;
      window.clearInterval(fallbackInterval);
      clearSocketFlush();
      setWsConnected(false);
      socketClient.close();
    };
  }, [flushSocketPayload, hydrateFleet, setWsConnected]);

  return (
    <div className="app-shell">
      <AppHeader systemHealthy={systemHealthy} wsConnected={wsConnected} wsStatusLabel={wsStatusLabel} />

      <section className="dashboard-grid">
        {/* Left Column (70%) */}
        <div className="dashboard-column">
          <FleetMap
            vehicles={deferredMapVehicles}
            selectedVehicleId={selectedVehicleId}
            onSelect={handleVehicleSelect}
          />
          <AlertPanel alerts={alerts} />
        </div>

        {/* Right Column (30%) */}
        <div className="dashboard-column">
          <VehicleDetailPanel details={selectedVehicleDetails} loading={loadingVehicle} />
          <VehicleTable
            vehicles={pagedVehicles}
            selectedVehicleId={selectedVehicleId}
            onSelect={handleVehicleSelect}
            loading={loadingFleet}
            filterText={filterText}
            onFilterTextChange={setFilterText}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            fleetSummary={fleetSummary}
            searchNotFound={searchNotFound}
            pageStart={pageStart}
            pageEnd={pageEnd}
            totalCount={filteredVehicles.length}
            currentPage={currentPageIndex + 1}
            totalPages={totalPages}
            canPreviousPage={currentPageIndex > 0}
            canNextPage={currentPageIndex < totalPages - 1}
            onPreviousPage={() => setPageIndex((value) => Math.max(0, value - 1))}
            onNextPage={() => setPageIndex((value) => Math.min(totalPages - 1, value + 1))}
          />
        </div>
      </section>

      <FooterBar />
    </div>
  );
}
