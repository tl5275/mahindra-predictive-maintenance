import { memo, useEffect, useMemo, useRef, useState } from "react";
import { FixedSizeList as List } from "react-window";

import { formatNumber, statusLabel } from "../utils/formatters";

const ROW_HEIGHT = 44;
const MAX_VISIBLE_ROWS = 12;
const MIN_VISIBLE_ROWS = 5;

const VehicleRow = memo(function VehicleRow({ data, index, style }) {
  const vehicle = data.vehicles[index];
  if (!vehicle) {
    return null;
  }

  const isSelected = vehicle.vehicle_id === data.selectedVehicleId;
  return (
    <article
      className={`vehicle-row ${isSelected ? "vehicle-row--selected" : ""}`}
      style={{
        ...style,
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between"
      }}
      onClick={() => data.onSelect(vehicle.vehicle_id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          data.onSelect(vehicle.vehicle_id);
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "16px", fontSize: "14px", width: "100%", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <strong style={{ width: "80px", color: "var(--ink)", fontWeight: "700", letterSpacing: "0.2px" }}>{vehicle.vehicle_id}</strong>
          <span style={{ width: "40px", color: "var(--ink)", fontWeight: "600" }}>{formatNumber(vehicle.health, 0)}%</span>
          <span style={{ width: "60px", color: "var(--ink)", fontWeight: "600" }}>{vehicle.rul}h</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: "500", color: `var(--${vehicle.status === 'warning' ? 'warning' : vehicle.status === 'critical' ? 'critical' : 'success'})` }}>
          <span className={`map-legend__dot map-legend__dot--${vehicle.status || "healthy"}`}></span>
          <span>{statusLabel(vehicle.status)}</span>
        </div>
      </div>
    </article>
  );
}, areRowsEqual);

function areRowsEqual(previous, next) {
  const previousVehicle = previous.data.vehicles[previous.index];
  const nextVehicle = next.data.vehicles[next.index];
  return (
    previous.style.top === next.style.top &&
    previous.style.height === next.style.height &&
    previous.style.width === next.style.width &&
    previousVehicle === nextVehicle &&
    previous.data.selectedVehicleId === next.data.selectedVehicleId &&
    previous.data.onSelect === next.data.onSelect
  );
}

function VehicleRowSkeleton({ index }) {
  return (
    <div className="vehicle-row vehicle-row--skeleton" key={`skeleton-${index}`}>
      <div className="skeleton-line skeleton-line--title" />
      <div className="skeleton-line" />
      <div className="skeleton-line skeleton-line--short" />
    </div>
  );
}

export default function VehicleTable({
  vehicles,
  selectedVehicleId,
  onSelect,
  loading,
  filterText,
  onFilterTextChange,
  statusFilter,
  onStatusFilterChange,
  fleetSummary,
  searchNotFound,
  pageStart,
  pageEnd,
  totalCount,
  currentPage,
  totalPages,
  canPreviousPage,
  canNextPage,
  onPreviousPage,
  onNextPage,
}) {
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0 });
  const [maxListHeight, setMaxListHeight] = useState(() =>
    typeof window === "undefined" ? MAX_VISIBLE_ROWS * ROW_HEIGHT : Math.floor(window.innerHeight * 0.7),
  );
  const itemData = useMemo(
    () => ({
      vehicles,
      onSelect,
      selectedVehicleId,
    }),
    [onSelect, selectedVehicleId, vehicles],
  );
  const listHeight = useMemo(() => {
    const preferredHeight = Math.max(Math.min(vehicles.length, MAX_VISIBLE_ROWS), MIN_VISIBLE_ROWS) * ROW_HEIGHT;
    return Math.min(preferredHeight, maxListHeight);
  }, [maxListHeight, vehicles.length]);

  useEffect(() => {
    if (!containerRef.current) {
      return undefined;
    }

    const observer = new ResizeObserver(([entry]) => {
      const width = entry.contentRect.width;
      setDimensions({ width });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const updateViewportHeight = () => setMaxListHeight(Math.floor(window.innerHeight * 0.7));
    updateViewportHeight();
    window.addEventListener("resize", updateViewportHeight);
    return () => window.removeEventListener("resize", updateViewportHeight);
  }, []);

  return (
    <section className="panel panel--feed">
      <div className="panel__header" style={{ marginBottom: "12px", borderBottom: "1px solid rgba(0,0,0,0.04)", paddingBottom: "16px" }}>
        <div>
          <h2 className="label-text">Fleet Feed</h2>
        </div>
        <span className="sub-text">{formatNumber(fleetSummary.averageHealth, 1)}% avg health</span>
      </div>

      <div className="vehicle-controls">
        <label className="toolbar__field">
          <span>Search</span>
          <input
            value={filterText}
            onChange={(event) => onFilterTextChange(event.target.value)}
            placeholder="Vehicle ID or model"
          />
        </label>

        <label className="toolbar__field">
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => onStatusFilterChange(event.target.value)}>
            <option value="all">All</option>
            <option value="healthy">Healthy</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
          </select>
        </label>
      </div>

      <div className="vehicle-table-shell" ref={containerRef}>
        {loading && vehicles.length === 0 ? (
          <div className="skeleton-stack">
            {Array.from({ length: 4 }, (_, index) => (
              <VehicleRowSkeleton index={index} key={index} />
            ))}
          </div>
        ) : vehicles.length === 0 ? (
          <div className="empty-state">
            <strong>{searchNotFound ? "Vehicle not found." : "No vehicles match the selected filters."}</strong>
            <span>
              {searchNotFound
                ? "Try a different vehicle ID or clear the search."
                : "Adjust the search or status filter to expand the fleet view."}
            </span>
          </div>
        ) : dimensions.width > 0 ? (
          <List
            className="vehicle-table-list"
            height={listHeight}
            itemCount={vehicles.length}
            itemData={itemData}
            itemSize={ROW_HEIGHT}
            width={dimensions.width}
          >
            {VehicleRow}
          </List>
        ) : null}
      </div>

      <div className="pagination-bar" style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid rgba(0,0,0,0.04)" }}>
        <span className="sub-text">
          {totalCount === 0 ? "0 vehicles" : `${pageStart}-${pageEnd} of ${formatNumber(totalCount)}`}
        </span>
        <div className="pagination-bar__controls">
          <button disabled={!canPreviousPage} onClick={onPreviousPage} type="button" style={{ border: "none", background: "transparent", color: "var(--ink)", fontWeight: "500", fontSize: "13px", cursor: canPreviousPage ? "pointer" : "default", opacity: canPreviousPage ? 1 : 0.3 }}>
            Prev
          </button>
          <span className="sub-text" style={{ fontSize: "12px" }}>{`${currentPage}/${Math.max(totalPages, 1)}`}</span>
          <button disabled={!canNextPage} onClick={onNextPage} type="button" style={{ border: "none", background: "transparent", color: "var(--ink)", fontWeight: "500", fontSize: "13px", cursor: canNextPage ? "pointer" : "default", opacity: canNextPage ? 1 : 0.3 }}>
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
