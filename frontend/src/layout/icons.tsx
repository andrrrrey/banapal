// Иконки навигации — SVG перенесены 1:1 из утверждённого прототипа.
import type { ReactNode } from "react";

function Svg({ children }: { children: ReactNode }) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
      {children}
    </svg>
  );
}

export const DashboardIcon = () => (
  <Svg>
    <rect x="3" y="3" width="7" height="9" rx="1.5" />
    <rect x="14" y="3" width="7" height="5" rx="1.5" />
    <rect x="14" y="12" width="7" height="9" rx="1.5" />
    <rect x="3" y="16" width="7" height="5" rx="1.5" />
  </Svg>
);

export const MonitorIcon = () => (
  <Svg>
    <path d="M3 12h4l2 6 4-14 2 8h6" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const AnalyticsIcon = () => (
  <Svg>
    <path d="M4 4v16h16" strokeLinecap="round" />
    <path d="M4 15l4-4 3 3 6-7" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="19" cy="7" r="1.6" />
  </Svg>
);

export const RomiIcon = () => (
  <Svg>
    <circle cx="12" cy="12" r="8.5" />
    <path
      d="M12 7v10M9.5 9.2c0-1.2 1.1-1.8 2.5-1.8s2.5.7 2.5 1.9c0 2.6-5 1.4-5 4 0 1.2 1.1 1.9 2.5 1.9s2.5-.7 2.5-1.8"
      strokeLinecap="round"
    />
  </Svg>
);

export const AiIcon = () => (
  <Svg>
    <path d="M12 3l1.9 4.2L18 9l-4.1 1.8L12 15l-1.9-4.2L6 9l4.1-1.8L12 3z" strokeLinejoin="round" />
    <path
      d="M18.5 15l.8 1.8 1.8.8-1.8.8-.8 1.8-.8-1.8-1.8-.8 1.8-.8.8-1.8z"
      strokeLinejoin="round"
    />
  </Svg>
);

export const AdminIcon = () => (
  <Svg>
    <circle cx="12" cy="12" r="3" />
    <path
      d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"
      strokeLinecap="round"
    />
  </Svg>
);
