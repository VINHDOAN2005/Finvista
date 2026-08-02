import React, { useEffect, useRef, useState } from "react";

import { DEFAULT_PREFERENCES } from "../../app/config.js";
import { formatChartValue, formatMoney } from "../../lib/formatters.js";

export function InteractiveLineChart({
  title,
  subtitle,
  series,
  markers = [],
  language = "vi",
  valueSuffix = "",
  chartPreferences = DEFAULT_PREFERENCES,
  height = 260,
  className = ""
}) {
  const isEnglish = language === "en";
  const chartRef = useRef(null);
  const dragRef = useRef(null);
  const [viewStart, setViewStart] = useState(0);
  const [viewSize, setViewSize] = useState(0);
  const [hoverIndex, setHoverIndex] = useState(null);
  const [hoverPoint, setHoverPoint] = useState(null);
  const [yPan, setYPan] = useState(0);

  const allDates = series[0]?.points?.map((point) => point.date) || [];
  const total = allDates.length;
  const width = 760;
  const padding = { top: 22, right: 92, bottom: 34, left: 16 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const zoomRates = {
    slow: { in: 0.88, out: 1.14 },
    normal: { in: 0.75, out: 1.25 },
    fast: { in: 0.6, out: 1.45 }
  };
  const panRates = {
    slow: 0.65,
    normal: 1,
    fast: 1.55
  };
  const zoomRate = zoomRates[chartPreferences.zoomSpeed] || zoomRates.normal;
  const panRate = panRates[chartPreferences.panSpeed] || panRates.normal;

  useEffect(() => {
    const initialSize = Math.min(total, 60);
    setViewStart(Math.max(0, total - initialSize));
    setViewSize(initialSize);
    setYPan(0);
    setHoverIndex(null);
    setHoverPoint(null);
  }, [total, title]);

  const safeViewSize = Math.max(2, Math.min(viewSize || total || 2, total || 2));
  const safeStart = Math.max(0, Math.min(viewStart, Math.max(0, total - safeViewSize)));
  const visibleDates = allDates.slice(safeStart, safeStart + safeViewSize);
  const visibleSeries = series.map((item) => {
    const points = item.points.slice(safeStart, safeStart + safeViewSize);
    if (item.scaleMode !== "relative-visible") {
      return { ...item, points };
    }
    const base = points
      .map((point) => Number(point.value))
      .find((value) => Number.isFinite(value) && value > 0) || 1;
    return {
      ...item,
      points: points.map((point) => {
        const rawValue = Number(point.value);
        return {
          ...point,
          tooltipValue: point.tooltipValue ?? point.value,
          value: Number.isFinite(rawValue) ? ((rawValue / base) - 1) * 100 : 0
        };
      })
    };
  });

  const values = visibleSeries.flatMap((item) =>
    item.points.map((point) => Number(point.value)).filter((value) => !Number.isNaN(value))
  );
  const minValue = values.length ? Math.min(...values) : 0;
  const maxValue = values.length ? Math.max(...values) : 1;
  const range = maxValue - minValue || 1;
  const paddedMin = minValue - range * 0.08;
  const paddedMax = maxValue + range * 0.08;
  const paddedRange = paddedMax - paddedMin || 1;

  function xFor(index) {
    if (visibleDates.length <= 1) return padding.left + plotWidth / 2;
    return padding.left + (index / (visibleDates.length - 1)) * plotWidth;
  }

  function yFor(value) {
    return padding.top + (1 - (Number(value) - (paddedMin + yPan)) / paddedRange) * plotHeight;
  }

  function pathFor(points) {
    return points
      .map((point, index) => `${index === 0 ? "M" : "L"} ${xFor(index)} ${yFor(point.value)}`)
      .join(" ");
  }

  function clampView(nextStart, nextSize = safeViewSize) {
    const size = Math.max(2, Math.min(nextSize, total || 2));
    const start = Math.max(0, Math.min(nextStart, Math.max(0, total - size)));
    setViewSize(size);
    setViewStart(start);
  }

  function zoom(direction) {
    if (total <= 2) return;
    const nextSize = direction === "in"
      ? Math.max(4, Math.round(safeViewSize * zoomRate.in))
      : Math.min(total, Math.round(safeViewSize * zoomRate.out));
    const center = safeStart + safeViewSize / 2;
    clampView(Math.round(center - nextSize / 2), nextSize);
  }

  function resetZoom() {
    const initialSize = total || 0;
    setYPan(0);
    clampView(Math.max(0, total - initialSize), initialSize);
  }

  function handleWheel(event) {
    event.preventDefault();
    event.stopPropagation();
    zoom(event.deltaY > 0 ? "out" : "in");
  }

  useEffect(() => {
    const element = chartRef.current;
    if (!element) return undefined;

    function onWheel(event) {
      event.preventDefault();
      event.stopPropagation();
      handleWheel(event);
    }

    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [safeStart, safeViewSize, total, chartPreferences.zoomSpeed]);

  function handlePointerDown(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    dragRef.current = {
      x: event.clientX,
      y: event.clientY,
      start: safeStart,
      startYPan: yPan,
      pointerId: event.pointerId
    };
  }

  function handlePointerMove(event) {
    if (dragRef.current) {
      event.preventDefault();
      event.stopPropagation();
    }
    const bounds = chartRef.current?.getBoundingClientRect();
    if (!bounds) return;

    const localX = Math.max(0, Math.min(event.clientX - bounds.left, bounds.width));
    const localY = Math.max(0, Math.min(event.clientY - bounds.top, bounds.height));
    
    const svgX = (localX / bounds.width) * width;
    const svgY = (localY / bounds.height) * height;
    
    setHoverPoint({
      x: svgX,
      y: svgY
    });
    const relativePlotX = (svgX - padding.left) / plotWidth;
    const clampedPlotX = Math.max(0, Math.min(relativePlotX, 1));
    const hovered = Math.max(
      0,
      Math.min(visibleDates.length - 1, Math.round(clampedPlotX * (visibleDates.length - 1)))
    );
    setHoverIndex(hovered);

    if (!dragRef.current) return;
    
    // Horizontal panning
    const deltaX = event.clientX - dragRef.current.x;
    const stepWidth = bounds.width / Math.max(safeViewSize, 1);
    const movedSteps = Math.round((deltaX / Math.max(stepWidth, 1)) * panRate);
    
    // Vertical panning
    const deltaY = event.clientY - dragRef.current.y;
    const deltaYPrice = (deltaY / plotHeight) * paddedRange;
    
    setYPan(dragRef.current.startYPan + deltaYPrice);
    clampView(dragRef.current.start - movedSteps, safeViewSize);
  }

  function handlePointerUp() {
    if (dragRef.current?.pointerId !== undefined) {
      chartRef.current?.releasePointerCapture?.(dragRef.current.pointerId);
    }
    dragRef.current = null;
  }

  const hoverDate = hoverIndex !== null ? visibleDates[hoverIndex] : null;
  const hoverValues = hoverIndex !== null
    ? visibleSeries.map((item) => ({
        label: item.label,
        color: item.color,
        value: item.points[hoverIndex]?.tooltipValue ?? item.points[hoverIndex]?.value,
        suffix: item.valueSuffix || valueSuffix
      }))
    : [];

  const activeDate = hoverDate || visibleDates[visibleDates.length - 1] || "";
  const activeValues = hoverIndex !== null
    ? hoverValues
    : visibleSeries.map((item) => ({
        label: item.label,
        color: item.color,
        value: item.points[item.points.length - 1]?.tooltipValue ?? item.points[item.points.length - 1]?.value,
        suffix: item.valueSuffix || valueSuffix
      }));

  const tooltipStyle = {
    left: `${hoverPoint?.x ?? 0}px`,
    top: `${hoverPoint?.y ?? 0}px`
  };

  if (!total) {
    return (
      <article className={`chart-card ${className}`}>
        <div className="chart-header">
          <div>
            <span>{subtitle}</span>
            <h3>{title}</h3>
          </div>
        </div>
        <div className="chart-empty">
          {isEnglish ? "No chart data available." : "Chưa có dữ liệu để vẽ chart."}
        </div>
      </article>
    );
  }

  return (
    <article className={`chart-card ${className}`}>
      <div className="chart-header">
        <div>
          <span>{subtitle}</span>
          <h3>{title}</h3>
        </div>
        <div className="chart-toolbar">
          <button onClick={() => zoom("in")}>+</button>
          <button onClick={() => zoom("out")}>-</button>
          <button onClick={resetZoom}>{isEnglish ? "Reset" : "Đặt lại"}</button>
        </div>
      </div>

      <div className="chart-legend">
        {series.map((item) => (
          <span key={item.key}>
            <i style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
      </div>

      <div
        ref={chartRef}
        className="interactive-chart"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onPointerLeave={() => {
          if (!dragRef.current) {
            setHoverIndex(null);
            setHoverPoint(null);
          }
        }}
      >
        {activeDate ? (
          <div className="chart-info-header">
            <span className="candle-date"><strong>{activeDate}</strong></span>
            {activeValues.map((item) => (
              <span key={item.label} className="info-item">
                {item.label}: <strong className="val">{formatChartValue(item.value, item.suffix)}</strong>
              </span>
            ))}
          </div>
        ) : null}

        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
          {[0, 0.25, 0.5, 0.75, 1].map((step) => {
            const y = padding.top + step * plotHeight;
            const value = (paddedMax + yPan) - step * paddedRange;
            return (
              <g key={step}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} className="grid-line" />
                <text x={width - padding.right + 12} y={y + 4} textAnchor="start" className="axis-label">
                  {formatChartValue(value, valueSuffix)}
                </text>
              </g>
            );
          })}

          {visibleDates.map((date, index) => (
            <text
              key={date}
              x={xFor(index)}
              y={height - 10}
              textAnchor={index === 0 ? "start" : index === visibleDates.length - 1 ? "end" : "middle"}
              className="axis-label"
            >
              {index === 0 || index === visibleDates.length - 1 ? date.slice(5) : ""}
            </text>
          ))}

          {visibleSeries.map((item) => (
            <path
              key={item.key}
              d={pathFor(item.points)}
              fill="none"
              stroke={item.color}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ))}

          {markers.map((marker) => {
            const y = yFor(marker.value);
            if (y < padding.top || y > padding.top + plotHeight) return null;
            return (
              <g key={marker.label}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} className="marker-line" />
                <text x={width - padding.right - 8} y={y - 6} textAnchor="end" className="marker-label">
                  {marker.label}
                </text>
              </g>
            );
          })}

          <line x1={width - padding.right} y1={padding.top} x2={width - padding.right} y2={height - padding.bottom} className="axis-border-line" />
          <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} className="axis-border-line" />

          {hoverIndex !== null && hoverPoint ? (
            <>
              <line
                x1={xFor(hoverIndex)}
                y1={padding.top}
                x2={xFor(hoverIndex)}
                y2={height - padding.bottom}
                className="hover-line"
              />
              <line
                x1={padding.left}
                y1={hoverPoint.y}
                x2={width - padding.right}
                y2={hoverPoint.y}
                className="hover-line"
              />
              {hoverPoint.y >= padding.top && hoverPoint.y <= padding.top + plotHeight && (() => {
                const price = (paddedMax + yPan) - ((hoverPoint.y - padding.top) / plotHeight) * paddedRange;
                return (
                  <g className="axis-badge-y">
                    <rect
                      x={width - padding.right}
                      y={hoverPoint.y - 9}
                      width={padding.right}
                      height={18}
                      className="badge-rect"
                      rx="2"
                    />
                    <text
                      x={width - padding.right + 6}
                      y={hoverPoint.y + 4}
                      className="badge-text"
                      textAnchor="start"
                    >
                      {formatChartValue(price, valueSuffix)}
                    </text>
                  </g>
                );
              })()}
              {hoverDate && (
                <g className="axis-badge-x">
                  <rect
                    x={xFor(hoverIndex) - 35}
                    y={height - padding.bottom}
                    width={70}
                    height={18}
                    className="badge-rect"
                    rx="2"
                  />
                  <text
                    x={xFor(hoverIndex)}
                    y={height - padding.bottom + 12}
                    className="badge-text"
                    textAnchor="middle"
                  >
                    {hoverDate.slice(5)}
                  </text>
                </g>
              )}
            </>
          ) : null}
        </svg>
      </div>

      <p className="chart-help">
        {isEnglish
          ? "Drag to pan, scroll to zoom, hover to inspect values."
          : "Kéo để xem ngang, lăn chuột để zoom, rê chuột để xem giá trị."}
      </p>
    </article>
  );
}

export function CandlestickChart({
  title,
  subtitle,
  candles,
  language = "vi",
  valueSuffix = "",
  className = "",
  height = 320
}) {
  const isEnglish = language === "en";
  const chartRef = useRef(null);
  const dragRef = useRef(null);
  const [viewStart, setViewStart] = useState(0);
  const [viewSize, setViewSize] = useState(0);
  const [hoverIndex, setHoverIndex] = useState(null);
  const [hoverPoint, setHoverPoint] = useState(null);
  const [yPan, setYPan] = useState(0);
  const width = 760;
  const padding = { top: 24, right: 92, bottom: 78, left: 16 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const volumeTop = height - 56;
  const volumeHeight = 34;
  const total = candles.length;

  useEffect(() => {
    const initialSize = Math.min(total, 60);
    setViewStart(Math.max(0, total - initialSize));
    setViewSize(initialSize);
    setYPan(0);
    setHoverIndex(null);
    setHoverPoint(null);
  }, [total, title]);

  const safeViewSize = Math.max(2, Math.min(viewSize || total || 2, total || 2));
  const safeStart = Math.max(0, Math.min(viewStart, Math.max(0, total - safeViewSize)));
  const visibleCandles = candles.slice(safeStart, safeStart + safeViewSize);
  const candleWidth = Math.max(1, Math.min(22, (plotWidth / Math.max(visibleCandles.length, 1)) * 0.72));
  const values = visibleCandles.flatMap((item) => [item.high, item.low]).filter((value) => Number.isFinite(value));
  const minValue = values.length ? Math.min(...values) : 0;
  const maxValue = values.length ? Math.max(...values) : 1;
  const range = maxValue - minValue || 1;
  const paddedMin = minValue - range * 0.08;
  const paddedMax = maxValue + range * 0.08;
  const paddedRange = paddedMax - paddedMin || 1;

  function xFor(index) {
    if (visibleCandles.length <= 1) return padding.left + plotWidth / 2;
    const margin = candleWidth / 2 + 5;
    const availableWidth = plotWidth - margin * 2;
    return padding.left + margin + (index / (visibleCandles.length - 1)) * availableWidth;
  }

  function yFor(value) {
    return padding.top + (1 - (Number(value) - (paddedMin + yPan)) / paddedRange) * plotHeight;
  }

  function clampView(nextStart, nextSize = safeViewSize) {
    const size = Math.max(2, Math.min(nextSize, total || 2));
    const start = Math.max(0, Math.min(nextStart, Math.max(0, total - size)));
    setViewSize(size);
    setViewStart(start);
  }

  function zoom(direction) {
    if (total <= 2) return;
    const nextSize = direction === "in"
      ? Math.max(4, Math.round(safeViewSize * 0.75))
      : Math.min(total, Math.round(safeViewSize * 1.25));
    const center = safeStart + safeViewSize / 2;
    clampView(Math.round(center - nextSize / 2), nextSize);
  }

  function resetZoom() {
    const initialSize = total || 0;
    setYPan(0);
    clampView(Math.max(0, total - initialSize), initialSize);
  }

  useEffect(() => {
    const element = chartRef.current;
    if (!element) return undefined;

    function onWheel(event) {
      event.preventDefault();
      event.stopPropagation();
      zoom(event.deltaY > 0 ? "out" : "in");
    }

    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [safeStart, safeViewSize, total]);

  function handlePointerDown(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    dragRef.current = {
      x: event.clientX,
      y: event.clientY,
      start: safeStart,
      startYPan: yPan,
      pointerId: event.pointerId
    };
  }

  function handlePointerMove(event) {
    if (dragRef.current) {
      event.preventDefault();
      event.stopPropagation();
    }
    const bounds = chartRef.current?.getBoundingClientRect();
    if (!bounds) return;

    const localX = Math.max(0, Math.min(event.clientX - bounds.left, bounds.width));
    const localY = Math.max(0, Math.min(event.clientY - bounds.top, bounds.height));
    
    const svgX = (localX / bounds.width) * width;
    const svgY = (localY / bounds.height) * height;
    
    setHoverPoint({
      x: svgX,
      y: svgY
    });
    const relativePlotX = (svgX - padding.left) / plotWidth;
    const clampedPlotX = Math.max(0, Math.min(relativePlotX, 1));
    const hovered = Math.max(
      0,
      Math.min(visibleCandles.length - 1, Math.round(clampedPlotX * (visibleCandles.length - 1)))
    );
    setHoverIndex(hovered);

    if (!dragRef.current) return;
    
    // Horizontal panning
    const deltaX = event.clientX - dragRef.current.x;
    const stepWidth = bounds.width / Math.max(safeViewSize, 1);
    const movedSteps = Math.round(deltaX / Math.max(stepWidth, 1));
    
    // Vertical panning
    const deltaY = event.clientY - dragRef.current.y;
    const deltaYPrice = (deltaY / plotHeight) * paddedRange;
    
    setYPan(dragRef.current.startYPan + deltaYPrice);
    clampView(dragRef.current.start - movedSteps, safeViewSize);
  }

  function handlePointerUp() {
    if (dragRef.current?.pointerId !== undefined) {
      chartRef.current?.releasePointerCapture?.(dragRef.current.pointerId);
    }
    dragRef.current = null;
  }

  const hoverCandle = hoverIndex !== null ? visibleCandles[hoverIndex] : null;
  const tooltipStyle = {
    left: `${hoverPoint?.x ?? 0}px`,
    top: `${hoverPoint?.y ?? 0}px`
  };
  const maxVolume = Math.max(...visibleCandles.map((item) => Number(item.volume) || 0), 1);
  const maPoints = visibleCandles.map((item, index) => {
    const globalIndex = safeStart + index;
    const window = candles.slice(Math.max(0, globalIndex - 4), globalIndex + 1);
    const avg = window.reduce((sum, candle) => sum + Number(candle.close || 0), 0) / Math.max(window.length, 1);
    return { date: item.date, value: avg };
  });
  const maPath = maPoints
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xFor(index)} ${yFor(point.value)}`)
    .join(" ");

  if (!candles.length) {
    return (
      <article className={`chart-card ${className}`}>
        <div className="chart-header">
          <div>
            <span>{subtitle}</span>
            <h3>{title}</h3>
          </div>
        </div>
        <div className="chart-empty">
          {isEnglish ? "No OHLC data available." : "Chưa có dữ liệu OHLC."}
        </div>
      </article>
    );
  }

  const activeCandle = hoverCandle || visibleCandles[visibleCandles.length - 1] || null;

  const volumeMaPoints = visibleCandles.map((item, index) => {
    const globalIndex = safeStart + index;
    const window = candles.slice(Math.max(0, globalIndex - 8), globalIndex + 1);
    const avg = window.reduce((sum, candle) => sum + Number(candle.volume || 0), 0) / Math.max(window.length, 1);
    return { date: item.date, value: avg };
  });

  const volumeMaPath = volumeMaPoints
    .map((point, index) => {
      const x = xFor(index);
      const volumeBarHeight = (Number(point.value) / maxVolume) * volumeHeight;
      const y = volumeTop + volumeHeight - volumeBarHeight;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  return (
    <article className={`chart-card fireant-card ${className}`}>
      <div className="chart-header">
        <div>
          <span>{subtitle}</span>
          <h3>{title}</h3>
        </div>
        <div className="chart-toolbar">
          <button onClick={() => zoom("in")}>+</button>
          <button onClick={() => zoom("out")}>-</button>
          <button onClick={resetZoom}>{isEnglish ? "Reset" : "Đặt lại"}</button>
        </div>
      </div>
      <div className="chart-legend candle-legend" style={{ display: "flex", gap: "0.8rem" }}>
        <span><i style={{ background: "#26a69a" }} />{isEnglish ? "Up" : "Tăng"}</span>
        <span><i style={{ background: "#ef5350" }} />{isEnglish ? "Down" : "Giảm"}</span>
        <span><i style={{ background: "#5a9bd2" }} />MA5</span>
        <span><i style={{ background: "#f89e35" }} />Vol SMA9</span>
      </div>
      <div
        ref={chartRef}
        className="interactive-chart candle-chart"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onPointerLeave={() => {
          if (!dragRef.current) {
            setHoverIndex(null);
            setHoverPoint(null);
          }
        }}
      >
        {activeCandle ? (
          <div className="chart-info-header" style={{ display: "flex", flexWrap: "wrap", gap: "0.8rem", fontSize: "0.8rem", paddingBottom: "8px" }}>
            <span className="candle-date"><strong>{activeCandle.date}</strong></span>
            <span className="info-item">O <strong className="info-val">{formatMoney(activeCandle.open)}</strong></span>
            <span className="info-item">H <strong className="info-val">{formatMoney(activeCandle.high)}</strong></span>
            <span className="info-item">L <strong className="info-val">{formatMoney(activeCandle.low)}</strong></span>
            <span className="info-item">C <strong className="info-val">{formatMoney(activeCandle.close)}</strong></span>
            {(() => {
              const change = activeCandle.close - activeCandle.open;
              const pct = (change / (activeCandle.open || 1)) * 100;
              const color = change >= 0 ? "#26a69a" : "#ef5350";
              const sign = change >= 0 ? "+" : "";
              return (
                <span className="info-item" style={{ color }}>
                  <strong>{sign}{formatMoney(change)} ({sign}{pct.toFixed(2)}%)</strong>
                </span>
              );
            })()}
            <span className="info-item">Vol <strong className="info-val">{formatMoney(activeCandle.volume)}</strong></span>
          </div>
        ) : null}

        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
          {[0, 0.25, 0.5, 0.75, 1].map((step) => {
            const y = padding.top + step * plotHeight;
            const value = (paddedMax + yPan) - step * paddedRange;
            return (
              <g key={`h-grid-${step}`}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} className="grid-line" />
                <text x={width - padding.right + 12} y={y + 4} textAnchor="start" className="axis-label">
                  {formatChartValue(value, valueSuffix)}
                </text>
              </g>
            );
          })}
          {[0, 0.25, 0.5, 0.75, 1].map((step) => {
            const x = padding.left + step * plotWidth;
            return (
              <line key={`v-grid-${step}`} x1={x} y1={padding.top} x2={x} y2={height - padding.bottom} className="grid-line" style={{ stroke: "rgba(148, 163, 184, 0.12)" }} />
            );
          })}
          {visibleCandles.map((item, index) => {
            const x = xFor(index);
            const up = item.close >= item.open;
            const color = up ? "#26a69a" : "#ef5350";
            const bodyTop = yFor(Math.max(item.open, item.close));
            const bodyBottom = yFor(Math.min(item.open, item.close));
            const bodyHeight = Math.max(1, bodyBottom - bodyTop);
            const volumeBarHeight = ((Number(item.volume) || 0) / maxVolume) * volumeHeight;
            return (
              <g key={item.date}>
                <line x1={x} y1={yFor(item.high)} x2={x} y2={yFor(item.low)} stroke={color} strokeWidth={candleWidth > 4 ? "1.5" : "1"} />
                <rect
                  x={x - candleWidth / 2}
                  y={bodyTop}
                  width={Math.max(1, candleWidth)}
                  height={bodyHeight}
                  rx={candleWidth > 5 ? "1" : "0"}
                  fill={color}
                  stroke={color}
                  strokeWidth={candleWidth > 4 ? "1" : "0"}
                />
                <rect
                  x={x - candleWidth / 2}
                  y={volumeTop + volumeHeight - volumeBarHeight}
                  width={Math.max(1, candleWidth)}
                  height={Math.max(1, volumeBarHeight)}
                  fill={up ? "rgba(38,166,154,0.34)" : "rgba(239,83,80,0.34)"}
                />
                {(index === 0 || index === visibleCandles.length - 1) ? (
                  <text x={x} y={height - 10} textAnchor={index === 0 ? "start" : "end"} className="axis-label" style={{ fill: "#94a3b8" }}>
                    {item.date.slice(5)}
                  </text>
                ) : null}
              </g>
            );
          })}
          <path
            d={maPath}
            fill="none"
            stroke="#5a9bd2"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={volumeMaPath}
            fill="none"
            stroke="#f89e35"
            strokeWidth="1.2"
            strokeDasharray="2 2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <text x={padding.left} y={volumeTop + 5} textAnchor="start" className="axis-label volume-axis-label" style={{ fill: "#94a3b8" }}>
            Vol
          </text>
          <line x1={width - padding.right} y1={padding.top} x2={width - padding.right} y2={height - padding.bottom} className="axis-border-line" style={{ stroke: "rgba(148, 163, 184, 0.28)" }} />
          <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} className="axis-border-line" style={{ stroke: "rgba(148, 163, 184, 0.28)" }} />

          {hoverIndex !== null && hoverPoint ? (
            <>
              <line
                x1={xFor(hoverIndex)}
                y1={padding.top}
                x2={xFor(hoverIndex)}
                y2={height - padding.bottom}
                className="hover-line"
                style={{ stroke: "#ffffff", opacity: 0.25 }}
              />
              <line
                x1={padding.left}
                y1={hoverPoint.y}
                x2={width - padding.right}
                y2={hoverPoint.y}
                className="hover-line"
                style={{ stroke: "#ffffff", opacity: 0.25 }}
              />
              {hoverPoint.y >= padding.top && hoverPoint.y <= padding.top + plotHeight && (() => {
                const price = (paddedMax + yPan) - ((hoverPoint.y - padding.top) / plotHeight) * paddedRange;
                return (
                  <g className="axis-badge-y">
                    <rect
                      x={width - padding.right}
                      y={hoverPoint.y - 9}
                      width={padding.right}
                      height={18}
                      className="badge-rect"
                      style={{ fill: "#1e293b", stroke: "#475569" }}
                      rx="2"
                    />
                    <text
                      x={width - padding.right + 6}
                      y={hoverPoint.y + 4}
                      className="badge-text"
                      style={{ fill: "#f8fafc" }}
                      textAnchor="start"
                    >
                      {formatChartValue(price, valueSuffix)}
                    </text>
                  </g>
                );
              })()}
              {hoverCandle && (
                <g className="axis-badge-x">
                  <rect
                    x={xFor(hoverIndex) - 35}
                    y={height - padding.bottom}
                    width={70}
                    height={18}
                    className="badge-rect"
                    style={{ fill: "#1e293b", stroke: "#475569" }}
                    rx="2"
                  />
                  <text
                    x={xFor(hoverIndex)}
                    y={height - padding.bottom + 12}
                    className="badge-text"
                    style={{ fill: "#f8fafc" }}
                    textAnchor="middle"
                  >
                    {hoverCandle.date.slice(5)}
                  </text>
                </g>
              )}
            </>
          ) : null}
        </svg>
      </div>
      <p className="chart-help">
        {isEnglish
          ? "Drag to pan, scroll to zoom, hover to inspect OHLC."
          : "Kéo để xem ngang/dọc, lăn chuột để zoom, rê chuột để xem OHLC."}
      </p>
    </article>
  );
}
