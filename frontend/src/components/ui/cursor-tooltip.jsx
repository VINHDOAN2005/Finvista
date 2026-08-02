import React, { useState } from "react";
import { createPortal } from "react-dom";


export function pointFromEvent(event) {
  const viewportWidth = window.innerWidth || 1024;
  const viewportHeight = window.innerHeight || 768;
  function clamp(point) {
    return {
      x: Math.max(8, Math.min(point.x, viewportWidth - 190)),
      y: Math.max(24, Math.min(point.y, viewportHeight - 24))
    };
  }
  if (Number.isFinite(event.clientX) && Number.isFinite(event.clientY)) {
    return clamp({ x: event.clientX, y: event.clientY });
  }
  const rect = event.currentTarget.getBoundingClientRect();
  return clamp({
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2
  });
}

export function CursorTooltip({ tooltip }) {
  if (!tooltip) return null;
  if (typeof document === "undefined") return null;
  return createPortal(
    <div className="app-tooltip cursor-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
      <strong>{tooltip.title}</strong>
      {tooltip.detail ? <span>{tooltip.detail}</span> : null}
    </div>,
    document.body
  );
}

export function useCursorTooltip() {
  const [tooltip, setTooltip] = useState(null);

  function showTooltip(event, nextTooltip) {
    const point = pointFromEvent(event);
    setTooltip({
      x: point.x,
      y: point.y,
      ...nextTooltip
    });
  }

  return {
    tooltip,
    showTooltip,
    hideTooltip: () => setTooltip(null)
  };
}
