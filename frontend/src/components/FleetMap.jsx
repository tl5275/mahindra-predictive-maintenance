import { memo, useCallback, useEffect, useMemo, useState } from "react";

import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMapEvents } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

import { formatNumber } from "../utils/formatters";

const INDIA_CENTER = [22.9734, 78.6569];
const CLUSTER_ONLY_ZOOM = 6;
const INDIVIDUAL_MARKER_ZOOM = 10;

function vehicleIcon(vehicle, isSelected) {
  const status = vehicle.status || "healthy";
  return L.divIcon({
    className: "map-pin-wrapper",
    html: `<span class="map-pin map-pin--${status} ${isSelected ? "map-pin--selected" : ""} map-legend__dot--pulse"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

function clusterIcon(cluster) {
  const count = cluster.getChildCount();
  return L.divIcon({
    className: "cluster-pin-wrapper",
    html: `<span class="cluster-pin">${count}</span>`,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
}

function hasValidCoordinates(vehicle) {
  return Number.isFinite(Number(vehicle.latitude)) && Number.isFinite(Number(vehicle.longitude));
}

function ViewportTracker({ onViewportChange }) {
  const map = useMapEvents({
    moveend() {
      onViewportChange(map);
    },
    zoomend() {
      onViewportChange(map);
    },
  });

  useEffect(() => {
    onViewportChange(map);
  }, [map, onViewportChange]);

  return null;
}

const FleetMarker = memo(function FleetMarker({ vehicle, isSelected, onSelect }) {
  const icon = useMemo(() => vehicleIcon(vehicle, isSelected), [isSelected, vehicle.status]);
  const eventHandlers = useMemo(
    () => ({
      click: () => onSelect(vehicle.vehicle_id),
    }),
    [onSelect, vehicle.vehicle_id],
  );

  return (
    <Marker
      position={[vehicle.latitude, vehicle.longitude]}
      icon={icon}
      eventHandlers={eventHandlers}
    >
      <Popup>
        <strong>{vehicle.vehicle_id}</strong>
        <div>{vehicle.model}</div>
        <div>Health {formatNumber(vehicle.health, 1)}</div>
        <div>RUL {vehicle.rul}h</div>
      </Popup>
    </Marker>
  );
});

function FleetMap({ vehicles, selectedVehicleId, onSelect }) {
  const [viewport, setViewport] = useState({
    zoom: 5,
    bounds: null,
  });

  const handleViewportChange = useCallback((map) => {
    setViewport({
      zoom: map.getZoom(),
      bounds: map.getBounds(),
    });
  }, []);

  const renderableVehicles = useMemo(() => {
    const mappableVehicles = vehicles.filter(hasValidCoordinates);
    if (!viewport.bounds) {
      return mappableVehicles;
    }

    return mappableVehicles.filter((vehicle) =>
      viewport.bounds.contains([Number(vehicle.latitude), Number(vehicle.longitude)]),
    );
  }, [vehicles, viewport.bounds]);

  return (
    <section className="panel panel--map">
      <div className="panel__header" style={{ marginBottom: "16px", padding: "24px 24px 0" }}>
        <div>
          <h2 className="label-text">Fleet Overview</h2>
        </div>
        <div className="map-legend" role="list" aria-label="Vehicle health legend">
          <span className="map-legend__item" role="listitem">
            <i className="map-legend__dot map-legend__dot--healthy" />
            <span className="sub-text">Healthy</span>
          </span>
          <span className="map-legend__item" role="listitem">
            <i className="map-legend__dot map-legend__dot--warning" />
            <span className="sub-text">Warning</span>
          </span>
          <span className="map-legend__item" role="listitem">
            <i className="map-legend__dot map-legend__dot--critical" />
            <span className="sub-text">Critical</span>
          </span>
        </div>
      </div>
      <div className="map-shell">
        <MapContainer center={INDIA_CENTER} zoom={5} scrollWheelZoom className="fleet-map">
          <ViewportTracker onViewportChange={handleViewportChange} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <MarkerClusterGroup
            animate={false}
            chunkedLoading
            disableClusteringAtZoom={INDIVIDUAL_MARKER_ZOOM}
            iconCreateFunction={clusterIcon}
            maxClusterRadius={viewport.zoom < CLUSTER_ONLY_ZOOM ? 80 : 48}
            removeOutsideVisibleBounds
            showCoverageOnHover={false}
            spiderfyOnMaxZoom={false}
          >
            {renderableVehicles.map((vehicle) => (
              <FleetMarker
                key={vehicle.vehicle_id}
                vehicle={vehicle}
                isSelected={vehicle.vehicle_id === selectedVehicleId}
                onSelect={onSelect}
              />
            ))}
          </MarkerClusterGroup>
        </MapContainer>
      </div>
    </section>
  );
}

export default memo(FleetMap);
