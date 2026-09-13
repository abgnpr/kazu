import { AppShell, Badge, Group, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";

import { PriceChart } from "./components/PriceChart";
import { ScreenerTable } from "./components/ScreenerTable";
import { StatusBar } from "./components/StatusBar";

export function App() {
  const [selected, setSelected] = useState<string | null>("RELIANCE");

  return (
    <AppShell header={{ height: 52 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Title order={4}>Kazu</Title>
            <Badge variant="light" size="xs">
              v0.1.0
            </Badge>
          </Group>
          <StatusBar />
        </Group>
      </AppShell.Header>

      <AppShell.Main h="100vh">
        <Stack gap="md" h="calc(100vh - 52px - var(--mantine-spacing-md) * 2)">
          <div style={{ flex: "0 0 42%", minHeight: 280 }}>
            <PriceChart symbol={selected} />
          </div>
          <Stack gap={4} style={{ flex: 1, minHeight: 0 }}>
            <Text size="xs" tt="uppercase" fw={600} c="dimmed">
              Screener
            </Text>
            <ScreenerTable selected={selected} onSelect={setSelected} />
          </Stack>
        </Stack>
      </AppShell.Main>
    </AppShell>
  );
}
