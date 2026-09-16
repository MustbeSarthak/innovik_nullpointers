import { useState, useEffect, useCallback, useRef } from 'react';

/* ── Haversine distance (km) ─────────────────────────────── */
function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/* ── Overpass API query for nearby hospitals ──────────────── */
async function fetchHospitals(lat, lon, radiusMeters = 5000) {
  const query = `
    [out:json][timeout:15];
    (
      node["amenity"="hospital"](around:${radiusMeters},${lat},${lon});
      way["amenity"="hospital"](around:${radiusMeters},${lat},${lon});
      relation["amenity"="hospital"](around:${radiusMeters},${lat},${lon});
    );
    out center tags;
  `;
  const res = await fetch('https://overpass-api.de/api/interpreter', {
    method: 'POST',
    body: `data=${encodeURIComponent(query)}`,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  if (!res.ok) throw new Error('Failed to fetch hospitals');
  const data = await res.json();

  return data.elements
    .map((el) => {
      const elLat = el.lat ?? el.center?.lat;
      const elLon = el.lon ?? el.center?.lon;
      if (!elLat || !elLon) return null;

      const tags = el.tags || {};
      const name = tags.name || tags['name:en'] || 'Unnamed Hospital';
      const phone =
        tags.phone || tags['contact:phone'] || tags['phone:mobile'] || '';
      const street = tags['addr:street'] || '';
      const city = tags['addr:city'] || '';
      const houseNum = tags['addr:housenumber'] || '';
      const address = [houseNum, street, city].filter(Boolean).join(', ') || 'Address not available';

      return {
        id: el.id,
        name,
        phone,
        address,
        lat: elLat,
        lon: elLon,
        dist: haversine(lat, lon, elLat, elLon),
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.dist - b.dist);
}

/* ── Inline SVG icons ──────────────────────────────────────── */
const HospitalIcon = ({ size = 20 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4" />
    <path d="M9 9h1M9 13h1M9 17h1" />
  </svg>
);

const PhoneIcon = ({ size = 16 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" />
  </svg>
);

const LocationIcon = ({ size = 16 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);

const CloseIcon = ({ size = 20 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2.5}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M18 6L6 18M6 6l12 12" />
  </svg>
);

const DirectionIcon = ({ size = 14 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="3 11 22 2 13 21 11 13 3 11" />
  </svg>
);

/* ══════════════════════════════════════════════════════════ */
export default function NearbyHospitals() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hospitals, setHospitals] = useState([]);
  const [error, setError] = useState('');
  const [userPos, setUserPos] = useState(null);
  const panelRef = useRef(null);

  /* Get location + hospitals */
  const locate = useCallback(async () => {
    setLoading(true);
    setError('');
    setHospitals([]);
    setOpen(true);

    try {
      const pos = await new Promise((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
        }),
      );
      const { latitude: lat, longitude: lon } = pos.coords;
      setUserPos({ lat, lon });

      const list = await fetchHospitals(lat, lon);
      if (list.length === 0) {
        setError('No hospitals found within 5 km. Try expanding your search.');
      }
      setHospitals(list);
    } catch (err) {
      if (err.code === 1) {
        setError('Location access denied. Please enable location permissions.');
      } else if (err.code === 2) {
        setError('Location unavailable. Please try again.');
      } else if (err.code === 3) {
        setError('Location request timed out. Please try again.');
      } else {
        setError('Could not fetch nearby hospitals. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  /* Close on backdrop click */
  const handleBackdrop = (e) => {
    if (panelRef.current && !panelRef.current.contains(e.target)) {
      setOpen(false);
    }
  };

  /* Close on Escape */
  useEffect(() => {
    const handler = (e) => e.key === 'Escape' && setOpen(false);
    if (open) window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open]);

  /* Format distance */
  const fmtDist = (km) =>
    km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;

  return (
    <>
      {/* ── Floating trigger button ──────────────────────────── */}
      <button
        id="find-hospital-btn"
        className="hosp-fab"
        onClick={locate}
        aria-label="Find Near Hospital"
      >
        <span className="hosp-fab-pulse" />
        <HospitalIcon size={18} />
        <span>Find Near Hospital</span>
      </button>

      {/* ── Slide-up panel ───────────────────────────────────── */}
      {open && (
        <div className="hosp-overlay" onClick={handleBackdrop}>
          <div className="hosp-panel" ref={panelRef}>
            {/* Header */}
            <div className="hosp-panel-header">
              <div className="hosp-panel-title-row">
                <div className="hosp-panel-icon">
                  <HospitalIcon size={20} />
                </div>
                <div>
                  <h2 className="hosp-panel-title">Nearby Hospitals</h2>
                  <p className="hosp-panel-sub">
                    {loading
                      ? 'Searching...'
                      : hospitals.length > 0
                        ? `${hospitals.length} hospital${hospitals.length > 1 ? 's' : ''} found`
                        : 'Find hospitals near you'}
                  </p>
                </div>
              </div>
              <button
                className="hosp-close"
                onClick={() => setOpen(false)}
                aria-label="Close"
              >
                <CloseIcon size={18} />
              </button>
            </div>

            {/* Handle bar */}
            <div className="hosp-handle">
              <span />
            </div>

            {/* Content */}
            <div className="hosp-panel-body">
              {loading && (
                <div className="hosp-loading">
                  <div className="hosp-loading-anim">
                    <span /><span /><span />
                  </div>
                  <p>Locating nearby hospitals…</p>
                </div>
              )}

              {error && !loading && (
                <div className="hosp-error">
                  <div className="hosp-error-icon">!</div>
                  <p>{error}</p>
                  <button className="btn btn-ghost btn-sm" onClick={locate}>
                    Try Again
                  </button>
                </div>
              )}

              {!loading && !error && hospitals.length > 0 && (
                <ul className="hosp-list">
                  {hospitals.map((h, i) => (
                    <li key={h.id} className="hosp-item fade-in" style={{ animationDelay: `${i * 0.06}s` }}>
                      <div className="hosp-item-rank">
                        {i === 0 ? (
                          <span className="hosp-nearest-badge">Nearest</span>
                        ) : (
                          <span className="hosp-rank-num">{i + 1}</span>
                        )}
                      </div>

                      <div className="hosp-item-body">
                        <h3 className="hosp-item-name">{h.name}</h3>

                        <div className="hosp-item-meta">
                          <span className="hosp-item-dist">
                            <DirectionIcon size={12} />
                            {fmtDist(h.dist)}
                          </span>
                        </div>

                        <div className="hosp-item-detail">
                          <LocationIcon size={13} />
                          <span>{h.address}</span>
                        </div>

                        {h.phone && (
                          <div className="hosp-item-detail">
                            <PhoneIcon size={13} />
                            <span>{h.phone}</span>
                          </div>
                        )}
                      </div>

                      <div className="hosp-item-actions">
                        {h.phone ? (
                          <a
                            href={`tel:${h.phone.replace(/[^+\d]/g, '')}`}
                            className="hosp-call-btn"
                            aria-label={`Call ${h.name}`}
                          >
                            <PhoneIcon size={15} />
                            <span>Call</span>
                          </a>
                        ) : (
                          <a
                            href={`https://www.google.com/maps/dir/?api=1&destination=${h.lat},${h.lon}${userPos ? `&origin=${userPos.lat},${userPos.lon}` : ''}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hosp-dir-btn"
                            aria-label={`Directions to ${h.name}`}
                          >
                            <DirectionIcon size={14} />
                            <span>Map</span>
                          </a>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
