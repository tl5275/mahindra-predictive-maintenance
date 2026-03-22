import { renderDigitalTwinPanel } from "../components/DigitalTwinPanel.js";

export function renderVehicleDetails(vehicleDetails) {
  if (!vehicleDetails) {
    return `<h2>Vehicle Digital Twin</h2><p class="small">Select a vehicle card to inspect details.</p>`;
  }

  const diagnosis = vehicleDetails.latest_diagnosis;
  const diagnosisHtml =
    diagnosis && diagnosis.issues && diagnosis.issues.length
      ? `<ul class="list">${diagnosis.issues
          .map((issue) => `<li>${issue.component}: ${issue.issue} (${issue.severity})</li>`)
          .join("")}</ul>`
      : `<p class="small">No active diagnosis alerts for this vehicle.</p>`;

  return `
    ${renderDigitalTwinPanel(vehicleDetails)}
    <h3 style="font-size: 0.92rem; margin: 10px 0 6px">Latest Diagnosis</h3>
    ${diagnosisHtml}
  `;
}
