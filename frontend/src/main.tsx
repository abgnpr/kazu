import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "./styles.css";

import { App } from "./App";
import { theme } from "./theme";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The data behind these queries is refreshed by the Python scheduler, not
      // by user actions, so aggressive refetching buys nothing.
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // In a packaged build the window opens while the sidecar is still
      // starting: PyInstaller unpacks, then DuckDB opens a database with
      // hundreds of sessions. That takes seconds, and the first few requests
      // are refused. Retry long enough to cover a cold start rather than
      // showing "Load failed" on a service that is merely still booting.
      retry: 8,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 5000),
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
);
