import { AppShell, Badge, Group, Stack, Tabs, Title } from "@mantine/core";
import { IconChartCandle, IconTable } from "@tabler/icons-react";
import { useState } from "react";

import { BreakoutTable } from "./components/BreakoutTable";
import { CoverageBar } from "./components/CoverageBar";
import { PriceChart } from "./components/PriceChart";
import { ScreenerTable } from "./components/ScreenerTable";
import { StatusBar } from "./components/StatusBar";

export function App() {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <AppShell header={{ height: 52 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Title order={4}>Kazu</Title>
            <Badge variant="light" size="xs">
              NSE
            </Badge>
          </Group>
          <StatusBar />
        </Group>
      </AppShell.Header>

      <AppShell.Main h="100vh">
        <Stack gap="sm" h="calc(100vh - 52px - var(--mantine-spacing-md) * 2)">
          <CoverageBar />

          <div style={{ flex: "0 0 38%", minHeight: 260 }}>
            <PriceChart symbol={selected} />
          </div>

          <Tabs defaultValue="breakouts" style={{ flex: 1, minHeight: 0 }}>
            <Tabs.List>
              <Tabs.Tab value="breakouts" leftSection={<IconChartCandle size={14} />}>
                Breakouts
              </Tabs.Tab>
              <Tabs.Tab value="screener" leftSection={<IconTable size={14} />}>
                All stocks
              </Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="breakouts" pt="xs">
              <BreakoutTable selected={selected} onSelect={setSelected} />
            </Tabs.Panel>
            <Tabs.Panel value="screener" pt="xs">
              <ScreenerTable selected={selected} onSelect={setSelected} />
            </Tabs.Panel>
          </Tabs>
        </Stack>
      </AppShell.Main>
    </AppShell>
  );
}
