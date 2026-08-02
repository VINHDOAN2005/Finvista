export const NAV_ITEMS = {
  vi: [
    { id: "intro", label: "Trang chủ" },
    { id: "market", label: "Tổng quan thị trường" },
    { id: "cw", label: "Cơ hội CW" },
    { id: "credit", label: "Sức khỏe tín dụng" },
    { id: "detail", label: "Chi tiết CW" }
  ],
  en: [
    { id: "intro", label: "Home" },
    { id: "market", label: "Market Overview" },
    { id: "cw", label: "CW Opportunities" },
    { id: "credit", label: "Credit Health" },
    { id: "detail", label: "CW Detail" }
  ]
};

export const DEFAULT_PREFERENCES = {
  theme: "soft",
  colorMode: "light",
  density: "comfortable",
  smoothMotion: true,
  tableHints: true,
  zoomSpeed: "normal",
  panSpeed: "normal"
};

export const STORAGE_KEYS = {
  language: "finvista-language",
  preferences: "finvista-preferences",
  filterPresets: "finvista-cw-filter-presets"
};

export const VN30_UNDERLYINGS = new Set([
  "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
  "LPB", "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI",
  "STB", "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]);

