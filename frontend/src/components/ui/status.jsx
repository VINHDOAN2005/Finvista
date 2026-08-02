import React from "react";


export function StatusPill({ health, loading, error, language = "vi" }) {
  const isEnglish = language === "en";
  if (loading) return <span className="status-pill muted">{isEnglish ? "Checking..." : "Đang kiểm tra..."}</span>;
  if (error) return <span className="status-pill danger">{isEnglish ? "Backend disconnected" : "Backend chưa kết nối"}</span>;
  if (health?.status === "healthy") {
    return <span className="status-pill success">{isEnglish ? "Backend healthy" : "Backend ổn định"}</span>;
  }
  return <span className="status-pill warning">{isEnglish ? "Backend warning" : "Backend cần kiểm tra"}</span>;
}


export function MetricCard({ label, value, tone = "default", detail }) {
  return (
    <article className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}


export function ErrorBox({ message, language = "vi" }) {
  return (
    <div className="notice error">
      <strong>{language === "en" ? "Error:" : "Lỗi:"}</strong> {message}
    </div>
  );
}


export function LoadingBox({ message }) {
  return <div className="notice loading">{message}</div>;
}
