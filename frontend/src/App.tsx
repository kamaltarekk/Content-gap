import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { apiGet } from "./api/client";

const queryClient = new QueryClient();

interface PublicConfig {
  environment: string;
  auth_mode: string;
  primary_language_default: string;
  limits: Record<string, number>;
}

function HealthPanel() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["public-config"],
    queryFn: () => apiGet<PublicConfig>("/api/v1/config/public"),
    retry: false,
  });

  return (
    <section style={{ fontFamily: "system-ui", maxWidth: 720, margin: "3rem auto", padding: "0 1rem" }}>
      <h1 dir="auto">تشخيص المحتوى والفجوات التنافسية</h1>
      <p dir="auto">Evidence-Based Content Diagnosis &amp; Competitive Gap Analysis — foundation.</p>
      {isLoading && <p>Connecting to backend…</p>}
      {error && <p style={{ color: "crimson" }}>Backend not reachable (this is expected until the API runs).</p>}
      {data && (
        <ul dir="auto">
          <li>environment: {data.environment}</li>
          <li>auth mode: {data.auth_mode}</li>
          <li>default language: {data.primary_language_default}</li>
        </ul>
      )}
    </section>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HealthPanel />
    </QueryClientProvider>
  );
}
