import { AppShell, Badge, Group, Stack, Tabs, Title } from "@mantine/core";
import { IconChartCandle, IconTable } from "@tabler/icons-react";
import { useState } from "react";

import { AboutMenu } from "./components/AboutMenu";
import { BreakoutTable } from "./components/BreakoutTable";
import { CoverageBar } from "./components/CoverageBar";
import { PriceChart } from "./components/PriceChart";
import { ScreenerTable } from "./components/ScreenerTable";
import { StatusBar } from "./components/StatusBar";
import { APP_NAME } from "./brand";

/** Panels are flex columns so a table can own the remaining height and scroll
 *  within it, rather than pushing the page past the viewport. */
const PANEL = {
  flex: 1,
  minHeight: 0,
  display: "flex",
  flexDirection: "column",
} as const;

export function App() {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <AppShell header={{ height: 52 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Title order={4}>{APP_NAME}</Title>
            <Badge variant="light" size="xs">
              NSE
            </Badge>
          </Group>
          <Group gap="xs">
            <StatusBar />
            <AboutMenu />
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Main h="100vh">
        <Stack gap="sm" h="calc(100vh - 52px - var(--mantine-spacing-md) * 2)">
          {/* Sizes to its own content: it must not take a share of the leftover
              height, or the table below shifts when the backfill alert collapses
              to its one-line form. */}
          <div style={{ flex: "0 0 auto" }}>
            <CoverageBar />
          </div>

          <div style={{ flex: "0 0 38%", minHeight: 260 }}>
            <PriceChart symbol={selected} />
          </div>

          {/* minHeight: 0 lets this flex child shrink below its content height,
              which is what allows the table inside to scroll instead of
              overflowing the viewport. */}
          <Tabs
            defaultValue="breakouts"
            style={{
              flex: 1,
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Tabs.List>
              <Tabs.Tab
                value="breakouts"
                leftSection={<IconChartCandle size={14} />}
              >
                Breakouts
              </Tabs.Tab>
              <Tabs.Tab value="screener" leftSection={<IconTable size={14} />}>
                All stocks
              </Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="breakouts" pt="xs" style={PANEL}>
              <BreakoutTable selected={selected} onSelect={setSelected} />
            </Tabs.Panel>
            <Tabs.Panel value="screener" pt="xs" style={PANEL}>
              <ScreenerTable selected={selected} onSelect={setSelected} />
            </Tabs.Panel>
          </Tabs>
        </Stack>
      </AppShell.Main>
    </AppShell>
  );
}
