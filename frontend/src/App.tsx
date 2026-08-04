import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { Link, Route, HashRouter as Router, Routes } from "react-router-dom";
import { apiGet } from "./api/client";
import Content from "./pages/Content";
import Setup from "./pages/Setup";

const queryClient = new QueryClient();

interface PublicConfig {
  environment: string;
  auth_mode: string;
  primary_language_default: string;
}

function Home() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["public-config"],
    queryFn: () => apiGet<PublicConfig>("/api/v1/config/public"),
    retry: false,
  });
  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 720, margin: "3rem auto", padding: "0 1rem" }}>
      <h1>تشخيص المحتوى والفجوات التنافسية</h1>
      <p>Evidence-Based Content Diagnosis &amp; Competitive Gap Analysis.</p>
      {isLoading && <p>Connecting to backend…</p>}
      {error && <p style={{ color: "crimson" }}>Backend not reachable (expected until the API runs).</p>}
      {data && (
        <ul>
          <li>environment: {data.environment}</li>
          <li>auth mode: {data.auth_mode}</li>
        </ul>
      )}
    </section>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <nav style={{ fontFamily: "system-ui", padding: "1rem", display: "flex", gap: "1rem" }}>
          <Link to="/">Home</Link>
          <Link to="/setup">Setup</Link>
          <Link to="/content">Content</Link>
        </nav>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/setup" element={<Setup />} />
          <Route path="/content" element={<Content />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}
