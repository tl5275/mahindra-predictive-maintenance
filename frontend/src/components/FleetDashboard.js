import { renderFleetOverview } from "../pages/FleetOverview.js";
import { renderFleetMap } from "./FleetMap.js";
import { renderVehicleCard } from "./VehicleCard.js";

export function renderFleetDashboard({ fleetData, selectedVehicleId }) {
  const overviewContainer = document.getElementById("fleet-overview");
  const vehicleGrid = document.getElementById("vehicle-grid");

  const vehicles = fleetData.vehicles || [];
  overviewContainer.innerHTML = `
    ${renderFleetOverview(fleetData)}
    <div class="panel" style="margin-bottom: 12px">${renderFleetMap(vehicles)}</div>
  `;

  vehicleGrid.innerHTML = vehicles.map((v) => renderVehicleCard(v, selectedVehicleId === v.vehicle_id)).join("");
}
