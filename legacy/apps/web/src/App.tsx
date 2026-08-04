import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
} from "react-router-dom";
import { Nav } from "./components/Nav";
import { getActiveProjectId } from "./project";
import { SetupPage } from "./pages/SetupPage";
import { GapsPage } from "./pages/GapsPage";
import { GapDetailPage } from "./pages/GapDetailPage";
import { CoveragePage } from "./pages/CoveragePage";
import { EvaluatePage } from "./pages/EvaluatePage";
import { ShadowPage } from "./pages/ShadowPage";
import { RunsPage } from "./pages/RunsPage";
import { ContinuationPage } from "./pages/ContinuationPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
});

/** Layout that requires an active project; redirects to /setup otherwise. */
function ProtectedLayout() {
  const projectId = getActiveProjectId();
  if (!projectId) {
    return <Navigate to="/setup" replace />;
  }
  return (
    <>
      <Nav />
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}

function SetupLayout() {
  return (
    <>
      <Nav />
      <main className="container">
        <SetupPage />
      </main>
    </>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/setup" element={<SetupLayout />} />
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<GapsPage />} />
            <Route path="/gaps/:gapId" element={<GapDetailPage />} />
            <Route path="/coverage" element={<CoveragePage />} />
            <Route path="/evaluate" element={<EvaluatePage />} />
            <Route path="/shadow" element={<ShadowPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/continuation" element={<ContinuationPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
