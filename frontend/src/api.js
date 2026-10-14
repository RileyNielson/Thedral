// Same origin by default so 127.0.0.1, localhost, and LAN addresses all work
// without CORS. Only the Vite dev server (port 5173) talks to a different port.
export const API_BASE = import.meta.env.VITE_API_BASE || (
  window.location.port === '5173'
    ? `http://${window.location.hostname}:8000`
    : window.location.origin
)
