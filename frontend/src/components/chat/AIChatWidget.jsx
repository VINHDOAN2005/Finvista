import React, { useEffect, useRef, useState, useCallback } from "react";
import { Bot, MessageSquare, Send, Trash2, User, X } from "lucide-react";
import { chatCompletion, getWarrantHistory } from "../../api.js";
import { InteractiveLineChart } from "../charts/WarrantCharts.jsx";
import { Button } from "../ui/button.jsx";
import { Input } from "../ui/input.jsx";

function findMatchingBrace(str, openPos) {
  let closePos = openPos;
  let counter = 1;
  while (counter > 0) {
    closePos++;
    if (closePos >= str.length) return -1;
    let c = str.charAt(closePos);
    if (c === '{') counter++;
    else if (c === '}') counter--;
  }
  return closePos;
}

function replaceFrac(text) {
  let index = text.indexOf("\\frac");
  while (index !== -1) {
    let firstOpen = text.indexOf("{", index + 5);
    if (firstOpen === -1) break;
    
    let firstClose = findMatchingBrace(text, firstOpen);
    if (firstClose === -1) break;
    
    let secondOpen = text.indexOf("{", firstClose + 1);
    if (secondOpen === -1 || secondOpen > firstClose + 3) {
      index = text.indexOf("\\frac", index + 5);
      continue;
    }
    
    let secondClose = findMatchingBrace(text, secondOpen);
    if (secondClose === -1) break;
    
    const num = replaceFrac(text.substring(firstOpen + 1, firstClose));
    const den = replaceFrac(text.substring(secondOpen + 1, secondClose));
    
    const html = `<span style="display:inline-flex;flex-direction:column;align-items:center;vertical-align:middle;margin:0 0.35em;font-size:0.92em">`
      + `<span style="border-bottom:1px solid currentColor;padding:0 6px 3px;white-space:nowrap">${num}</span>`
      + `<span style="padding:3px 6px 0;white-space:nowrap">${den}</span>`
      + `</span>`;
      
    text = text.substring(0, index) + html + text.substring(secondClose + 1);
    index = text.indexOf("\\frac");
  }
  return text;
}

function formatMathHtml(mathText) {
  if (!mathText) return "";
  let processed = replaceFrac(mathText);
  return processed
    .replace(/\\ /g, " ")
    .replace(/\\,/g, " ")
    .replace(/\\quad/g, "  ")
    .replace(/\\qquad/g, "    ")
    .replace(/\\&/g, "&")
    .replace(/\\\^/g, "^")
    .replace(/\\_/g, "_")
    .replace(/\\\{/g, "{")
    .replace(/\\\}/g, "}")
    .replace(/\\%/g, "%")
    .replace(/\\dots\b/g, "…")
    .replace(/\\cdots\b/g, "…")
    .replace(/\\times/g, "×")
    .replace(/\\cdot/g, "·")
    .replace(/\\pm/g, "±")
    .replace(/\\le\b/g, "≤")
    .replace(/\\ge\b/g, "≥")
    .replace(/\\ne\b/g, "≠")
    .replace(/\\approx\b/g, "≈")
    .replace(/\\in\b/g, "∈")
    .replace(/\\notin\b/g, "∉")
    .replace(/\\alpha\b/g, "α")
    .replace(/\\beta\b/g, "β")
    .replace(/\\delta\b/g, "δ")
    .replace(/\\epsilon\b/g, "ε")
    .replace(/\\sigma\b/g, "σ")
    .replace(/\\theta\b/g, "θ")
    .replace(/\\pi\b/g, "π")
    .replace(/\\infty\b/g, "∞")
    .replace(/\\Delta\b/g, "Δ")
    .replace(/\\Theta\b/g, "Θ")
    .replace(/\\Gamma\b/g, "Γ")
    .replace(/\\rightarrow\b/g, "→")
    .replace(/\\leftarrow\b/g, "←")
    .replace(/\\leftrightarrow\b/g, "↔")
    .replace(/\\Rightarrow\b/g, "⇒")
    .replace(/\\Leftarrow\b/g, "⇐")
    .replace(/\\Leftrightarrow\b/g, "⇔")
    .replace(/\\to\b/g, "→")
    .replace(/\\left\(/g, "(")
    .replace(/\\right\)/g, ")")
    .replace(/\\left\[/g, "[")
    .replace(/\\right\]/g, "]")
    .replace(/\\sqrt\{([^}]+)\}/g,
      '<span style="display:inline-flex;align-items:center;vertical-align:middle;margin:0 0.15em;">'
      + '<span style="font-size:1.15em;font-family:serif;margin-right:-0.05em;line-height:1;">√</span>'
      + '<span style="border-top:1px solid currentColor;padding:2px 2px 0;margin-left:-0.05em;font-size:0.95em;line-height:1;">$1</span>'
      + '</span>')
    .replace(/\\text\{([^}]+)\}/g, "$1")
    .replace(/\\sum_\{([^}]+)\}\^\{([^}]+)\}/g,
      '<span style="display:inline-flex;align-items:center;vertical-align:middle;margin:0 0.25em;">'
      + '<span style="display:inline-flex;flex-direction:column;align-items:center;line-height:0.95;font-size:0.85em;">'
      + '<span style="font-size:0.72em;padding-bottom:1px;font-family:sans-serif;">$2</span>'
      + '<span style="font-size:1.6em;font-family:serif;font-weight:normal;line-height:1;margin:-0.15em 0;">∑</span>'
      + '<span style="font-size:0.72em;padding-top:1px;font-family:sans-serif;">$1</span>'
      + '</span>'
      + '</span>')
    .replace(/\\sum_\{([^}]+)\}\^([0-9a-zA-Z])/g,
      '<span style="display:inline-flex;align-items:center;vertical-align:middle;margin:0 0.25em;">'
      + '<span style="display:inline-flex;flex-direction:column;align-items:center;line-height:0.95;font-size:0.85em;">'
      + '<span style="font-size:0.72em;padding-bottom:1px;font-family:sans-serif;">$2</span>'
      + '<span style="font-size:1.6em;font-family:serif;font-weight:normal;line-height:1;margin:-0.15em 0;">∑</span>'
      + '<span style="font-size:0.72em;padding-top:1px;font-family:sans-serif;">$1</span>'
      + '</span>'
      + '</span>')
    .replace(/\\sum_([0-9a-zA-Z])\^([0-9a-zA-Z])/g,
      '<span style="display:inline-flex;align-items:center;vertical-align:middle;margin:0 0.25em;">'
      + '<span style="display:inline-flex;flex-direction:column;align-items:center;line-height:0.95;font-size:0.85em;">'
      + '<span style="font-size:0.72em;padding-bottom:1px;font-family:sans-serif;">$2</span>'
      + '<span style="font-size:1.6em;font-family:serif;font-weight:normal;line-height:1;margin:-0.15em 0;">∑</span>'
      + '<span style="font-size:0.72em;padding-top:1px;font-family:sans-serif;">$1</span>'
      + '</span>'
      + '</span>')
    .replace(/\\sum_\{([^}]+)\}/g,
      '<span style="display:inline-flex;align-items:center;vertical-align:middle;margin:0 0.25em;">'
      + '<span style="display:inline-flex;flex-direction:column;align-items:center;line-height:0.95;font-size:0.85em;">'
      + '<span style="font-size:1.6em;font-family:serif;font-weight:normal;line-height:1;margin:-0.15em 0;">∑</span>'
      + '<span style="font-size:0.72em;padding-top:1px;font-family:sans-serif;">$1</span>'
      + '</span>'
      + '</span>')
    .replace(/\\sum_([0-9a-zA-Z])/g,
      '<span style="display:inline-flex;align-items:center;vertical-align:middle;margin:0 0.25em;">'
      + '<span style="display:inline-flex;flex-direction:column;align-items:center;line-height:0.95;font-size:0.85em;">'
      + '<span style="font-size:1.6em;font-family:serif;font-weight:normal;line-height:1;margin:-0.15em 0;">∑</span>'
      + '<span style="font-size:0.72em;padding-top:1px;font-family:sans-serif;">$1</span>'
      + '</span>'
      + '</span>')
    .replace(/\\sum\b/g, '<span style="font-size:1.6em;font-family:serif;vertical-align:middle;margin:0 0.2em;line-height:1;">∑</span>')
    .replace(/_\{([^}]+)\}/g, "<sub>$1</sub>")
    .replace(/_([0-9a-zA-Z])\b/g, "<sub>$1</sub>")
    .replace(/\^\{([^}]+)\}/g, "<sup>$1</sup>")
    .replace(/\^([0-9a-zA-Z])\b/g, "<sup>$1</sup>")
    .replace(/\{([^}]+)\}/g, "$1");
}

function parseInline(text) {
  if (!text) return "";

  let processed = text
    .replace(/\\ /g, " ")
    .replace(/\$\$/g, "$")
    .replace(/\\&/g, "&")
    .replace(/\\%/g, "%")
    .replace(/\\dots/g, "…")
    .replace(/\\cdots/g, "…")
    .replace(/\\le/g, "≤")
    .replace(/\\ge/g, "≥")
    .replace(/\\ne/g, "≠")
    .replace(/\\approx/g, "≈")
    .replace(/\\in/g, "∈")
    .replace(/\\notin/g, "∉")
    .replace(/\\times/g, "×")
    .replace(/\\pm/g, "±")
    .replace(/\\cdot/g, "·")
    .replace(/\\alpha/g, "α")
    .replace(/\\beta/g, "β")
    .replace(/\\delta/g, "δ")
    .replace(/\\epsilon/g, "ε")
    .replace(/\\sigma/g, "σ")
    .replace(/\\theta/g, "θ")
    .replace(/\\pi/g, "π")
    .replace(/\\infty/g, "∞")
    .replace(/\\Delta/g, "Δ")
    .replace(/\\Theta/g, "Θ")
    .replace(/\\Gamma/g, "Γ")
    .replace(/\\sum/g, "∑")
    .replace(/\\rightarrow\b/g, "→")
    .replace(/\\leftarrow\b/g, "←")
    .replace(/\\leftrightarrow\b/g, "↔")
    .replace(/\\Rightarrow\b/g, "⇒")
    .replace(/\\Leftarrow\b/g, "⇐")
    .replace(/\\Leftrightarrow\b/g, "⇔")
    .replace(/\\to\b/g, "→")
    .replace(/\\text\{([^}]+)\}/g, "$1");

  // Format fractions, square roots, and subscripts/superscripts natively
  processed = replaceFrac(processed);
  processed = processed
    .replace(/\\sqrt\{([^}]+)\}/g,
      '<span style="display:inline-flex;align-items:center;vertical-align:middle;margin:0 0.15em;">'
      + '<span style="font-size:1.15em;font-family:serif;margin-right:-0.05em;line-height:1;">√</span>'
      + '<span style="border-top:1px solid currentColor;padding:2px 2px 0;margin-left:-0.05em;font-size:0.95em;line-height:1;">$1</span>'
      + '</span>')
    .replace(/_\{([^}]+)\}/g, "<sub>$1</sub>")
    .replace(/_([0-9a-zA-Z])\b/g, "<sub>$1</sub>")
    .replace(/\^\{([^}]+)\}/g, "<sup>$1</sup>")
    .replace(/\^([0-9a-zA-Z])\b/g, "<sup>$1</sup>");

  // Format math blocks
  processed = processed.replace(/\$([^$]+)\$/g, (_, mathVal) => {
    return `<span style="font-style:italic;font-weight:600;font-family:serif;">${formatMathHtml(mathVal)}</span>`;
  });

  // Format Markdown syntax to HTML
  processed = processed
    .replace(/\*\*\*([^*\n]+)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>")
    .replace(/`([^`\n]+)`/g, '<code style="background:rgba(0,0,0,0.06);padding:0.1rem 0.3rem;border-radius:4px;font-size:0.85em;font-family:monospace;">$1</code>');

  // Auto-insert space between tags and letters to prevent sticking
  processed = processed
    .replace(/([A-Za-zÀ-ỹ0-9])(<em|<strong|<code|<span style="font-style:italic)/g, "$1 $2")
    .replace(/(<\/em>|<\/strong>|<\/code>|<\/span>)([A-Za-zÀ-ỹ0-9])/g, "$1 $2");

  return <span dangerouslySetInnerHTML={{ __html: processed }} />;
}

const chartCache = {};

function WarrantChatChart({ symbol, language = "vi" }) {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const isEnglish = language === "en";

  const fetchChartData = useCallback((force = false) => {
    if (!symbol) return;
    setLoading(true);
    setError("");
    
    const cacheKey = symbol.toUpperCase();
    const cached = chartCache[cacheKey];
    const now = Date.now();
    
    if (!force && cached && now - cached.timestamp < 5 * 60 * 1000) {
      setHistory(cached.data);
      setLoading(false);
      return;
    }
    
    getWarrantHistory(symbol.toUpperCase(), 60)
      .then((data) => {
        chartCache[cacheKey] = {
          data,
          timestamp: Date.now()
        };
        setHistory(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [symbol]);

  useEffect(() => {
    fetchChartData(false);
  }, [fetchChartData]);

  const handleRefresh = (e) => {
    e.stopPropagation();
    fetchChartData(true);
  };

  if (loading && !history) {
    return (
      <div style={{ padding: "1rem", textAlign: "center", fontSize: "0.8rem", color: "var(--text-muted, #94a3b8)" }}>
        <span className="dot-loader"></span>
        <span className="dot-loader" style={{ animationDelay: "0.2s" }}></span>
        <span className="dot-loader" style={{ animationDelay: "0.4s" }}></span>
        <span style={{ marginLeft: "0.5rem" }}>{isEnglish ? "Loading chart data..." : "Đang tải dữ liệu biểu đồ..."}</span>
      </div>
    );
  }

  if (error || !history || !history.history || history.history.length === 0) {
    return (
      <div style={{ padding: "0.5rem", fontSize: "0.75rem", color: "#ef4444", background: "rgba(239, 68, 68, 0.08)", borderRadius: "4px" }}>
        {isEnglish ? `Could not load chart for ${symbol}` : `Không thể tải biểu đồ cho ${symbol}`}
      </div>
    );
  }

  const historyRows = history.history;
  const rawPricePoints = (accessor) => {
    return historyRows.map((row) => ({
      date: row.date,
      value: accessor(row)
    }));
  };

  const isStock = history.averages?.valuation_assessment === "STOCK" || historyRows.every(r => r.warrant_price === 0);

  const chartSeries = [];
  if (!isStock) {
    chartSeries.push({
      key: "cw",
      label: isEnglish ? "CW price" : "Giá CW",
      color: "#ec4899",
      valueSuffix: " VND",
      scaleMode: "relative-visible",
      points: rawPricePoints((row) => row.warrant_price)
    });
  }
  chartSeries.push({
    key: "underlying",
    label: isStock ? (isEnglish ? "Stock Price" : "Giá cổ phiếu") : (isEnglish ? "Underlying price" : "Giá cơ sở"),
    color: "#3b82f6",
    valueSuffix: isStock ? " đ" : " VND",
    scaleMode: isStock ? "absolute" : "relative-visible",
    points: rawPricePoints((row) => row.underlying_price)
  });

  return (
    <div className="warrant-chat-chart-container" style={{
      background: "var(--bg-card, rgba(255, 255, 255, 0.03))",
      border: "1px solid var(--border-color, rgba(255, 255, 255, 0.08))",
      borderRadius: "8px",
      padding: "0.6rem 0.8rem",
      margin: "0.5rem 0",
      width: "100%",
      boxSizing: "border-box",
      overflow: "hidden"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <span style={{ fontSize: "0.8rem", fontWeight: "600", color: "var(--text-main, #ffffff)" }}>
          {isStock 
            ? (isEnglish ? `Stock Chart - ${symbol}` : `Biểu đồ cổ phiếu - ${symbol}`) 
            : (isEnglish ? `Interactive Chart - ${symbol}` : `Biểu đồ tương tác - ${symbol}`)}
        </span>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="chart-refresh-btn"
          title={isEnglish ? "Refresh chart data" : "Làm mới dữ liệu"}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              animation: loading ? "spin 1s linear infinite" : "none"
            }}
          >
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
          </svg>
        </button>
      </div>
      <div className="chat-chart-wrapper" style={{ height: "auto", position: "relative" }}>
        <InteractiveLineChart
          title=""
          subtitle=""
          series={chartSeries}
          language={language}
          valueSuffix={isStock ? " đ" : "%"}
          height={320}
        />
      </div>
    </div>
  );
}

function parseTextAndTables(text, onFollowUp, language = "vi") {
  const lines = text.split("\n");
  const elements = [];
  let currentTable = null;
  let currentList = null;
  let currentBlockquote = null;
  let inMathBlock = false;
  let mathBlockLines = [];
  let inCodeBlock = false;
  let codeBlockLines = [];
  let listKey = 0;
  let tableKey = 0;
  let pKey = 0;
  let hKey = 0;
  let bqKey = 0;
  let codeKey = 0;

  function flushList() {
    if (currentList) {
      const Tag = currentList.type;
      elements.push(
        <Tag
          key={`list-${listKey++}`}
          start={currentList.startNum ?? 1}
          style={{
            paddingLeft: "1.2rem",
            margin: "0.5rem 0",
            listStyleType: currentList.type === "ul" ? "disc" : "decimal"
          }}
        >
          {currentList.items.map((item, idx) => (
            <li key={idx} style={{ marginBottom: "0.25rem" }}>{parseInline(item)}</li>
          ))}
        </Tag>
      );
      currentList = null;
    }
  }

  function flushTable() {
    if (currentTable) {
      elements.push(
        <div key={`table-wrapper-${tableKey++}`} className="table-wrap compact" style={{ margin: "1rem 0", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
            <thead>
              <tr>
                {currentTable.headers.map((h, idx) => (
                  <th key={idx} style={{ padding: "0.4rem 0.6rem", borderBottom: "2px solid var(--border-color, #e2e8f0)", textAlign: currentTable.aligns[idx] || "left" }}>
                    {parseInline(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {currentTable.rows.map((row, rowIdx) => (
                <tr key={rowIdx} style={{ borderBottom: "1px solid var(--border-color, #edf2f7)" }}>
                  {row.map((cell, cellIdx) => (
                    <td key={cellIdx} style={{ padding: "0.4rem 0.6rem", textAlign: currentTable.aligns[cellIdx] || "left" }}>
                      {parseInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      currentTable = null;
    }
  }

  function flushBlockquote() {
    if (currentBlockquote) {
      elements.push(
        <blockquote
          key={`bq-${bqKey++}`}
          style={{
            margin: "0.75rem 0",
            padding: "0.6rem 1rem",
            borderLeft: "3px solid rgba(0, 139, 122, 0.5)",
            background: "rgba(0, 139, 122, 0.06)",
            borderRadius: "0 6px 6px 0",
            color: "var(--text-muted, #94a3b8)",
            fontSize: "0.85rem",
            fontStyle: "italic"
          }}
        >
          {currentBlockquote.map((item, idx) => (
            <div key={idx} style={{ marginBottom: idx < currentBlockquote.length - 1 ? "0.4rem" : "0" }}>
              {parseInline(item)}
            </div>
          ))}
        </blockquote>
      );
      currentBlockquote = null;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (inCodeBlock) {
      if (trimmed.startsWith("```")) {
        inCodeBlock = false;
        const codeText = codeBlockLines.join("\n");
        elements.push(
          <pre key={`code-${codeKey++}`}>
            <code>{codeText}</code>
          </pre>
        );
        codeBlockLines = [];
      } else {
        codeBlockLines.push(line);
      }
      continue;
    }

    const chartMatch = line.match(/\[CHART:\s*([A-Z0-9]{3,8})\]/i);
    if (chartMatch) {
      flushList();
      flushTable();
      flushBlockquote();
      const symbol = chartMatch[1].toUpperCase();
      const beforeText = line.replace(/\[CHART:\s*[A-Z0-9]{3,8}\]/i, "").trim();
      if (beforeText) {
        elements.push(
          <p key={`p-${pKey++}`} style={{ margin: "0.5rem 0", lineHeight: "1.5" }}>
            {parseInline(beforeText)}
          </p>
        );
      }
      elements.push(
        <WarrantChatChart key={`chart-${i}`} symbol={symbol} language={language} />
      );
      continue;
    }

    if (trimmed.startsWith("```")) {
      flushList();
      flushTable();
      flushBlockquote();
      inCodeBlock = true;
      codeBlockLines = [];
      continue;
    }

    if (trimmed !== ">" && !trimmed.startsWith("> ")) {
      flushBlockquote();
    }

    // Multi-line block math detection
    if (trimmed === "$$" || (trimmed.startsWith("$$") && !trimmed.endsWith("$$"))) {
      if (!inMathBlock) {
        flushList();
        flushTable();
        flushBlockquote();
        inMathBlock = true;
        const rest = trimmed === "$$" ? "" : trimmed.substring(2).trim();
        if (rest) {
          mathBlockLines = [rest];
        } else {
          mathBlockLines = [];
        }
        continue;
      } else {
        inMathBlock = false;
        const mathText = mathBlockLines.join(" ").trim();
        const isSimpleVariable = mathText.length < 15 &&
          !/[=>+*/<-]/.test(mathText) &&
          !mathText.includes("\\frac") &&
          !mathText.includes("\\sum") &&
          !mathText.includes("\\times") &&
          !mathText.includes("\\approx") &&
          !mathText.includes("\\le") &&
          !mathText.includes("\\ge") &&
          !mathText.includes("\\dots");
        elements.push(
          <div
            key={`math-multi-${i}`}
            className="math-block"
            style={{
              textAlign: isSimpleVariable ? "left" : "center",
              paddingLeft: isSimpleVariable ? "1.5rem" : "0.2rem",
              margin: isSimpleVariable ? "0.4rem 0" : "1.2rem 0",
              fontWeight: "600",
              fontSize: "1.05rem",
              lineHeight: "1.4",
              overflowX: "auto",
              maxWidth: "100%",
              paddingTop: "0.5rem",
              paddingBottom: "0.5rem",
              whiteSpace: "nowrap"
            }}
            dangerouslySetInnerHTML={{ __html: formatMathHtml(mathText) }}
          />
        );
        continue;
      }
    }

    if (inMathBlock) {
      if (trimmed === "$$" || trimmed.endsWith("$$")) {
        inMathBlock = false;
        const rest = trimmed === "$$" ? "" : trimmed.substring(0, trimmed.length - 2).trim();
        if (rest) {
          mathBlockLines.push(rest);
        }
        const mathText = mathBlockLines.join(" ").trim();
        const isSimpleVariable = mathText.length < 15 &&
          !/[=>+*/<-]/.test(mathText) &&
          !mathText.includes("\\frac") &&
          !mathText.includes("\\sum") &&
          !mathText.includes("\\times") &&
          !mathText.includes("\\approx") &&
          !mathText.includes("\\le") &&
          !mathText.includes("\\ge") &&
          !mathText.includes("\\dots");
        elements.push(
          <div
            key={`math-multi-end-${i}`}
            className="math-block"
            style={{
              textAlign: isSimpleVariable ? "left" : "center",
              paddingLeft: isSimpleVariable ? "1.5rem" : "0.2rem",
              margin: isSimpleVariable ? "0.4rem 0" : "1.2rem 0",
              fontWeight: "600",
              fontSize: "1.05rem",
              lineHeight: "1.4",
              overflowX: "auto",
              maxWidth: "100%",
              paddingTop: "0.5rem",
              paddingBottom: "0.5rem",
              whiteSpace: "nowrap"
            }}
            dangerouslySetInnerHTML={{ __html: formatMathHtml(mathText) }}
          />
        );
      } else {
        mathBlockLines.push(line);
      }
      continue;
    }

    // Standalone block math (single line)
    // Standalone block math (including bulleted / quoted math)
    const blockMathMatch = trimmed.match(/^[*\-+>\s]*\$\$((?:(?!\$\$).)*)\$\$$/);
    if (blockMathMatch) {
      flushList();
      flushTable();
      const mathText = blockMathMatch[1].trim();
      const isSimpleVariable = mathText.length < 15 &&
        !/[=>+*/<-]/.test(mathText) &&
        !mathText.includes("\\frac") &&
        !mathText.includes("\\sum") &&
        !mathText.includes("\\times") &&
        !mathText.includes("\\approx") &&
        !mathText.includes("\\le") &&
        !mathText.includes("\\ge") &&
        !mathText.includes("\\dots");
      elements.push(
        <div
          key={`math-${i}`}
          className="math-block"
          style={{
            textAlign: isSimpleVariable ? "left" : "center",
            paddingLeft: isSimpleVariable ? "1.5rem" : "0.2rem",
            margin: isSimpleVariable ? "0.4rem 0" : "1.2rem 0",
            fontWeight: "600",
            fontSize: "1.05rem",
            lineHeight: "1.4",
            overflowX: "auto",
            maxWidth: "100%",
            paddingTop: "0.5rem",
            paddingBottom: "0.5rem",
            whiteSpace: "nowrap"
          }}
          dangerouslySetInnerHTML={{ __html: formatMathHtml(mathText) }}
        />
      );
      continue;
    }

    // Table parsing
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      flushList();
      const cells = line.split("|").map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      const isSeparator = cells.every(c => c.startsWith(":") || c.endsWith("-") || c.startsWith("-"));

      if (isSeparator) {
        if (currentTable) {
          currentTable.aligns = cells.map(c => {
            if (c.startsWith(":") && c.endsWith(":")) return "center";
            if (c.endsWith(":")) return "right";
            return "left";
          });
        }
        continue;
      }

      if (!currentTable) {
        currentTable = { headers: cells, aligns: [], rows: [] };
      } else {
        currentTable.rows.push(cells);
      }
      continue;
    } else {
      flushTable();
    }

    // Unordered List
    if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
      const bulletText = trimmed.substring(2);
      if (!currentList || currentList.type !== "ul") {
        flushList();
        currentList = { type: "ul", items: [bulletText] };
      } else {
        currentList.items.push(bulletText);
      }
      continue;
    }

    // Ordered List
    const olMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (olMatch) {
      const itemText = olMatch[2];
      const itemNum = parseInt(olMatch[1]);
      if (!currentList || currentList.type !== "ol") {
        flushList();
        currentList = { type: "ol", items: [itemText], startNum: itemNum };
      } else {
        currentList.items.push(itemText);
      }
      continue;
    }

    flushList();

    // Headers
    if (trimmed.startsWith("#")) {
      const match = trimmed.match(/^(#{1,6})\s+(.*)/);
      if (match) {
        const level = match[1].length;
        const text = match[2];
        const Tag = `h${level}`;
        elements.push(
          <Tag key={`h-${hKey++}`} style={{ margin: "1rem 0 0.5rem 0", fontWeight: "600", color: "var(--text-main, #ffffff)" }}>
            {parseInline(text)}
          </Tag>
        );
        continue;
      }
    }

    // HR
    if (trimmed === "---" || trimmed === "***" || trimmed === "* * *") {
      elements.push(
        <hr key={`hr-${i}`} style={{ margin: "1rem 0", border: "0", borderTop: "1px solid var(--border-color, #e2e8f0)" }} />
      );
      continue;
    }

    // Blockquote
    if (trimmed === ">" || trimmed.startsWith("> ")) {
      flushList();
      flushTable();
      const quoteText = trimmed === ">" ? "" : trimmed.substring(2);
      if (!currentBlockquote) {
        currentBlockquote = [quoteText];
      } else {
        currentBlockquote.push(quoteText);
      }
      continue;
    }

    // Paragraph
    if (trimmed.length > 0) {
      elements.push(
        <p key={`p-${pKey++}`} style={{ margin: "0.5rem 0", lineHeight: "1.5" }}>
          {parseInline(line)}
        </p>
      );
    }
  }

  flushList();
  flushTable();
  flushBlockquote();
  if (inCodeBlock && codeBlockLines.length > 0) {
    const codeText = codeBlockLines.join("\n");
    elements.push(
      <pre key={`code-${codeKey++}`}>
        <code>{codeText}</code>
      </pre>
    );
  }
  return elements;
}

function normalizeLatex(content) {
  const MATH_KEYWORDS = /\\frac|\\sum|\\sqrt/;

  // Xử lý từng dòng
  const lines = content.split('\n');
  const processed = lines.map(line => {
    const trimmed = line.trim();

    // Bỏ qua dòng đã có $$
    if (trimmed.startsWith('$$') && trimmed.endsWith('$$')) return line;

    // Dòng chứa LaTeX keyword
    if (MATH_KEYWORDS.test(trimmed)) {
      let math = trimmed
        // Đổi HTML sub/sup → LaTeX TRƯỚC
        .replace(/<sub>(.*?)<\/sub>/g, '_{$1}')
        .replace(/<sup>(.*?)<\/sup>/g, '^{$1}');

      return `$$${math}$$`;
    }

    return line;
  });

  let result = processed.join('\n');

  // Dọn dẹp các $$ block đã có sẵn
  result = result.replace(/\$\$([\s\S]*?)\$\$/g, (_, inner) => {
    const fixed = inner
      .replace(/<sub>(.*?)<\/sub>/g, '_{$1}')
      .replace(/<sup>(.*?)<\/sup>/g, '^{$1}');
    return `$$${fixed}$$`;
  });

  return result;
}

function renderMessageContent(content, onFollowUp, language = "vi") {
  if (!content) return "";
  content = content.normalize("NFC");
  
  let cleanContent = content
    .replace(/<ElicitationsGroup\s+message="([^"]+)">/gi, "**$1**")
    .replace(/<\/ElicitationsGroup>/gi, "");

  const followUpRegex = /<(?:FollowUp|Elicitation)\s+label="([^"]+)"\s+query="([^"]+)"\s*(?:\/>|><\/(?:FollowUp|Elicitation)>)/gi;
  const followUps = [];
  cleanContent = cleanContent.replace(followUpRegex, (match, label, query) => {
    followUps.push({ label, query });
    return "";
  });

  const renderedElements = parseTextAndTables(cleanContent, onFollowUp, language);

  return (
    <>
      <div className="markdown-body">{renderedElements}</div>
      {followUps.length > 0 && (
        <div className="followups-container" style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
          {followUps.map((fp, i) => (
            <button
              key={i}
              className="followup-btn"
              onClick={() => onFollowUp(fp.query)}
              style={{
                background: "rgba(0, 139, 122, 0.08)",
                border: "1px solid rgba(0, 139, 122, 0.2)",
                color: "#008b7a",
                padding: "0.4rem 0.75rem",
                borderRadius: "16px",
                fontSize: "0.75rem",
                cursor: "pointer",
                fontWeight: "550",
                transition: "all 0.2s",
                display: "inline-flex",
                alignItems: "center"
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.background = "rgba(0, 139, 122, 0.15)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.background = "rgba(0, 139, 122, 0.08)";
                e.currentTarget.style.transform = "none";
              }}
            >
              {fp.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
}

export function AIChatWidget({ language = "vi" }) {
  const isEnglish = language === "en";
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const [chatSize, setChatSize] = useState({ width: 380, height: 480 });
  const isResizingRef = useRef(false);

  const handleResizeStart = (e, direction) => {
    e.preventDefault();
    isResizingRef.current = true;
    const startX = e.clientX;
    const startY = e.clientY;
    const startWidth = chatSize.width;
    const startHeight = chatSize.height;

    const handleMouseMove = (moveEvent) => {
      if (!isResizingRef.current) return;
      let newWidth = startWidth;
      let newHeight = startHeight;

      if (direction === "left" || direction === "both") {
        const dx = startX - moveEvent.clientX; // drag left to expand
        newWidth = Math.max(320, Math.min(window.innerWidth * 0.9, startWidth + dx));
      }
      if (direction === "top" || direction === "both") {
        const dy = startY - moveEvent.clientY; // drag up to expand
        newHeight = Math.max(380, Math.min(window.innerHeight * 0.85, startHeight + dy));
      }

      setChatSize({ width: newWidth, height: newHeight });
    };

    const handleMouseUp = () => {
      isResizingRef.current = false;
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  const SUGGESTIONS = isEnglish
    ? [
      "What is a Covered Warrant (CW)?",
      "How is the G-score calculated?",
      "Explain Altman Z-score risk zones",
      "What is Volatility Arbitrage?"
    ]
    : [
      "Chứng quyền có bảo đảm (CW) là gì?",
      "Điểm G-score được tính thế nào?",
      "Giải thích các phân vùng rủi ro Altman Z-score",
      "Volatility Arbitrage là gì?"
    ];

  useEffect(() => {
    // Initial welcome message
    const viWelcome = "Xin chào! Tôi là Cố vấn Tài chính AI của Finvista. Tôi có thể giúp gì cho bạn trong việc phân tích chứng quyền hoặc rủi ro tín dụng hôm nay?";
    const enWelcome = "Hello! I am your Finvista AI Financial Advisor. How can I help you analyze warrants or corporate credit risk today?";
    const expectedWelcome = isEnglish ? enWelcome : viWelcome;

    if (messages.length === 0) {
      setMessages([
        {
          role: "assistant",
          content: expectedWelcome
        }
      ]);
    } else if (messages.length === 1 && (messages[0].content === viWelcome || messages[0].content === enWelcome)) {
      if (messages[0].content !== expectedWelcome) {
        setMessages([
          {
            role: "assistant",
            content: expectedWelcome
          }
        ]);
      }
    }
  }, [language, isEnglish, messages]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  async function handleSendMessage(text) {
    const cleanText = text.trim();
    if (!cleanText || loading) return;

    const newMessages = [...messages, { role: "user", content: cleanText }];
    setMessages(newMessages);
    setInputValue("");
    setLoading(true);

    try {
      // Backend expects role to be "user" or "assistant"
      const apiMessages = newMessages.map(m => ({
        role: m.role,
        content: m.content
      }));

      const res = await chatCompletion(apiMessages);
      setMessages([...newMessages, { role: "assistant", content: res.response }]);
    } catch (err) {
      setMessages([...newMessages, {
        role: "assistant",
        content: isEnglish
          ? `Error: ${err.message}`
          : `Lỗi kết nối AI: ${err.message}`
      }]);
    } finally {
      setLoading(false);
    }
  }

  function handleClearHistory() {
    setMessages([
      {
        role: "assistant",
        content: isEnglish
          ? "Hello! I am your Finvista AI Financial Advisor. How can I help you analyze warrants or corporate credit risk today?"
          : "Xin chào! Tôi là Cố vấn Tài chính AI của Finvista. Tôi có thể giúp gì cho bạn trong việc phân tích chứng quyền hoặc rủi ro tín dụng hôm nay?"
      }
    ]);
  }

  return (
    <div className="ai-chat-widget-container">
      {/* Floating Toggle Button */}
      {!isOpen && (
        <button
          className="ai-chat-floating-trigger pulse-animation"
          onClick={() => setIsOpen(true)}
          aria-label="Open AI Advisor Chat"
        >
          <MessageSquare size={24} />
          <span className="badge-notification">AI</span>
        </button>
      )}

      {/* Chat Window Panel */}
      {isOpen && (
        <div
          className="ai-chat-window-panel"
          style={{ width: `${chatSize.width}px`, height: `${chatSize.height}px` }}
        >
          {/* Custom top-left resize handles */}
          <div
            onMouseDown={(e) => handleResizeStart(e, "both")}
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              width: "14px",
              height: "14px",
              cursor: "nwse-resize",
              zIndex: 1000,
            }}
          />
          <div
            onMouseDown={(e) => handleResizeStart(e, "left")}
            style={{
              position: "absolute",
              left: 0,
              top: "14px",
              bottom: 0,
              width: "6px",
              cursor: "ew-resize",
              zIndex: 1000,
            }}
          />
          <div
            onMouseDown={(e) => handleResizeStart(e, "top")}
            style={{
              position: "absolute",
              left: "14px",
              right: 0,
              top: 0,
              height: "6px",
              cursor: "ns-resize",
              zIndex: 1000,
            }}
          />
          {/* Header */}
          <div className="ai-chat-header">
            <div className="ai-chat-header-title">
              <Bot size={18} />
              <span>Finvista AI Advisor</span>
            </div>
            <div className="ai-chat-header-actions">
              <button onClick={handleClearHistory} title={isEnglish ? "Clear history" : "Xóa lịch sử"}>
                <Trash2 size={14} />
              </button>
              <button onClick={() => setIsOpen(false)} title={isEnglish ? "Close" : "Đóng"}>
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="ai-chat-messages-area">
            {messages.map((msg, idx) => {
              const isAssistant = msg.role === "assistant";
              return (
                <div key={idx} className={`chat-message-row ${isAssistant ? "assistant" : "user"}`}>
                  <div className="avatar">
                    {isAssistant ? <Bot size={14} /> : <User size={14} />}
                  </div>
                  <div className="bubble" style={{ maxWidth: "100%" }}>
                    {isAssistant ? (
                      renderMessageContent(msg.content, handleSendMessage, language)
                    ) : (
                      <p style={{ whiteSpace: "pre-line" }}>{msg.content}</p>
                    )}
                  </div>
                </div>
              );
            })}
            {loading && (
              <div className="chat-message-row assistant typing">
                <div className="avatar">
                  <Bot size={14} />
                </div>
                <div className="bubble">
                  <span className="dot-loader"></span>
                  <span className="dot-loader"></span>
                  <span className="dot-loader"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestion Chips */}
          {messages.length <= 2 && !loading && (
            <div className="ai-chat-suggestions-ribbon">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  className="suggestion-chip"
                  onClick={() => handleSendMessage(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input Area Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage(inputValue);
            }}
            className="ai-chat-input-row"
          >
            <Input
              type="text"
              placeholder={isEnglish ? "Type a message..." : "Nhập câu hỏi tài chính..."}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={loading}
              autoFocus
            />
            <Button type="submit" disabled={!inputValue.trim() || loading}>
              <Send size={14} />
            </Button>
          </form>
        </div>
      )}
    </div>
  );
}
