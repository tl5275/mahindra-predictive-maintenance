self.onmessage = (event) => {
  const { vehicles, filters } = event.data;
  const query = (filters.filterText || "").trim().toLowerCase();
  const statusFilter = filters.statusFilter || "all";
  const anomalyOnly = Boolean(filters.anomalyOnly);

  const visibleIds = vehicles
    .filter((vehicle) => {
      if (query) {
        const haystack = `${vehicle.vehicle_id} ${vehicle.model} ${vehicle.predicted_component || ""}`.toLowerCase();
        if (!haystack.includes(query)) {
          return false;
        }
      }

      if (statusFilter !== "all" && vehicle.health_status !== statusFilter) {
        return false;
      }

      if (anomalyOnly && !vehicle.anomaly_flag) {
        return false;
      }

      return true;
    })
    .map((vehicle) => vehicle.vehicle_id);

  self.postMessage({ visibleIds });
};
