const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  viewBox: '0 0 24 24',
};

export const IcHome = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);

export const IcAssess = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
  </svg>
);

export const IcBell = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
);

export const IcUser = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

export const IcSpark = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3zM19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z" />
  </svg>
);

export const IcChat = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M8 10h8M8 14h5M21 12a8.96 8.96 0 01-8 8.92A9 9 0 013.5 5.6 8.5 8.5 0 0121 12z" />
  </svg>
);

export const IcCamera = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M15 10l4.55-2.27A1 1 0 0121 8.6v6.8a1 1 0 01-1.45.9L15 14v-4zM3 6h9a2 2 0 012 2v8a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2z" />
  </svg>
);

export const IcSun = (p) => (
  <svg {...base} width={p.size || 16} height={p.size || 16}>
    <path d="M12 17a5 5 0 100-10 5 5 0 000 10zM12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4l1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
);

export const IcMoon = (p) => (
  <svg {...base} width={p.size || 16} height={p.size || 16}>
    <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
  </svg>
);

export const IcBack = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M15 19l-7-7 7-7" />
  </svg>
);

export const IcHeart = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
  </svg>
);

export const IcUpload = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
  </svg>
);

export const IcClock = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export const IcShield = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

export const IcCheck = (p) => (
  <svg {...base} strokeWidth={3} width={p.size || 14} height={p.size || 14}>
    <path d="M5 13l4 4L19 7" />
  </svg>
);

export const IcCare = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

export const IcWarn = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

export const IcPlus = (p) => (
  <svg {...base} width={p.size || 18} height={p.size || 18}>
    <path d="M12 4v16m8-8H4" />
  </svg>
);

export const IcLogout = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
);

export const IcDrop = (p) => (
  <svg {...base} width={p.size || 46} height={p.size || 46}>
    <path d="M12 3s6 6.5 6 11a6 6 0 11-12 0c0-4.5 6-11 6-11z" />
  </svg>
);

export const IcDoc = (p) => (
  <svg {...base} width={p.size || 20} height={p.size || 20}>
    <path d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
  </svg>
);