# Routes

## Routing model

The React + Vite SPA uses a small hash-route switch in `frontend/src/app/App.tsx`; React Router is not installed. All routes render inside the root `.app-shell` wrapper.

| URL | Component | File | Layout | Summary |
| --- | --- | --- | --- | --- |
| `#/` | `DashboardPage` | `frontend/src/features/dashboard/DashboardPage.tsx` | `App` root shell; page-local two-column dashboard/sidebar | Product home and module launcher for report self-check and PTR comparison. |
| `#/report-check` | `ReportCheckPage` | `frontend/src/features/report-check/pages/ReportCheckPage.tsx` | `App` root shell; centered upload/results page | Upload one inspection-report PDF, run C01-C11, inspect evidence and export results. |
| `#/ptr-compare` | `PTRComparePage` | `frontend/src/features/ptr-compare/pages/PTRComparePage.tsx` | `App` root shell; centered upload/results page | Upload PTR and report PDFs, compare clauses/tables, review findings and export. |
| any other hash | `DashboardPage` fallback | `frontend/src/features/dashboard/DashboardPage.tsx` | Same as `#/` | Unknown hashes fall back to the dashboard. |

## Full route configuration

```tsx
import { useEffect, useState } from "react";

import { DashboardPage } from "../features/dashboard/DashboardPage";
import { PTRComparePage } from "../features/ptr-compare/pages/PTRComparePage";
import { ReportCheckPage } from "../features/report-check/pages/ReportCheckPage";

export function App() {
  const [hash, setHash] = useState(() => window.location.hash || "#/");

  useEffect(() => {
    const handleHashChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const path = hash.replace("#", "") || "/";

  return (
    <div className="app-shell">
      {path === "/ptr-compare" ? (
        <PTRComparePage />
      ) : path === "/report-check" ? (
        <ReportCheckPage />
      ) : (
        <DashboardPage />
      )}
    </div>
  );
}
```
