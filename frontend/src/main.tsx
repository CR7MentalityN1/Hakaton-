import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Alert, CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { AuthProvider, useAuth } from "./auth/Auth";
import { ErrorBoundary } from "./components/common";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import Catalog from "./pages/Catalog";
import Universities, { UniversityDetail } from "./pages/Universities";
import Interactions, { InteractionDetail } from "./pages/Interactions";
import Workflows from "./pages/Workflows";
import Reports from "./pages/Reports";
import Import from "./pages/Import";
import { Audit, Settings, Integrations, Help } from "./pages/Admin";
import "./styles.css";
const theme = createTheme({
  palette: {
    primary: { main: "#6534b5" },
    secondary: { main: "#ed6635" },
    background: { default: "#f6f5f9" },
    text: { primary: "#252135", secondary: "#716c7e" },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
    button: { textTransform: "none" },
  },
  components: {
    MuiTableCell: {
      styleOverrides: {
        head: { background: "#f4f1f8", fontWeight: 700 },
        body: { paddingTop: 16, paddingBottom: 16 },
      },
    },
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
  },
});
function Guard({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles: string[];
}) {
  const { user } = useAuth();
  return roles.includes(user.role) ? children : <Navigate to="/403" replace />;
}
export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="universities" element={<Universities />} />
        <Route path="universities/:id" element={<UniversityDetail />} />
        <Route path="interactions" element={<Interactions />} />
        <Route path="interactions/:id" element={<InteractionDetail />} />
        {["directions", "programs", "products"].map((kind) => (
          <Route
            path={kind}
            key={kind}
            element={<Catalog key={kind} kind={kind} />}
          />
        ))}
        <Route path="workflows" element={<Workflows />} />
        <Route path="reports" element={<Reports />} />
        <Route
          path="import"
          element={
            <Guard roles={["admin", "manager"]}>
              <Import />
            </Guard>
          }
        />
        <Route
          path="users"
          element={
            <Guard roles={["admin"]}>
              <Catalog kind="users" />
            </Guard>
          }
        />
        <Route
          path="audit"
          element={
            <Guard roles={["admin"]}>
              <Audit />
            </Guard>
          }
        />
        <Route
          path="settings"
          element={
            <Guard roles={["admin"]}>
              <Settings />
            </Guard>
          }
        />
        <Route path="integrations" element={<Integrations />} />
        <Route path="help" element={<Help />} />
        <Route
          path="403"
          element={
            <Alert severity="warning">403 · Недостаточно прав доступа</Alert>
          }
        />
        <Route
          path="*"
          element={<Alert severity="info">404 · Страница не найдена</Alert>}
        />
      </Route>
    </Routes>
  );
}
const client = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 15000, refetchOnWindowFocus: true },
  },
});
ReactDOM.createRoot(document.getElementById("root")!).render(
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <ErrorBoundary>
      <QueryClientProvider client={client}>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </ThemeProvider>,
);
