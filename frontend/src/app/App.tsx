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
