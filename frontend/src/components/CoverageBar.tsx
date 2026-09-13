import { Alert, Button, Group, Progress, Text, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDatabaseImport } from "@tabler/icons-react";

import { useBackfill, useCoverage } from "../api/queries";

const NEEDED_FOR_200DMA = 200;

/** Shows how much history exists and offers the on-demand backfill.
 *  History matters here: the breakout screen needs ~250 sessions, and each
 *  session is one request to NSE, so this is never done automatically. */
export function CoverageBar() {
  const { data } = useCoverage();
  const backfill = useBackfill();

  if (!data) return null;

  const run = (days: number) =>
    backfill.mutate(days, {
      onSuccess: (r) =>
        notifications.show({
          title: "Backfill complete",
          message: `${r.dates} date(s) fetched, ${r.rows.toLocaleString("en-IN")} rows${
            r.failed ? `, ${r.failed} failed` : ""
          }`,
          color: r.failed ? "yellow" : "teal",
        }),
      onError: (e) =>
        notifications.show({ title: "Backfill failed", message: String(e), color: "red" }),
    });

  const pct = Math.min(100, (data.sessions / NEEDED_FOR_200DMA) * 100);

  if (data.has_200dma) {
    return (
      <Group gap="xs" justify="space-between">
        <Text size="xs" c="dimmed">
          {data.sessions} sessions · {data.symbols.toLocaleString("en-IN")} symbols ·{" "}
          {data.first_date} → {data.last_date}
        </Text>
        <Tooltip label="Fetch any older sessions still missing">
          <Button
            size="compact-xs"
            variant="subtle"
            leftSection={<IconDatabaseImport size={13} />}
            loading={backfill.isPending}
            onClick={() => run(800)}
          >
            Extend history
          </Button>
        </Tooltip>
      </Group>
    );
  }

  return (
    <Alert color="yellow" variant="light" p="xs">
      <Group justify="space-between" wrap="nowrap" gap="md">
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text size="xs" fw={600}>
            {data.sessions} of {NEEDED_FOR_200DMA} sessions needed for the 200 DMA
          </Text>
          <Text size="xs" c="dimmed">
            Breakout screening stays empty until enough history is downloaded. One request
            per trading day.
          </Text>
          <Progress value={pct} size="xs" mt={6} />
        </div>
        <Button
          size="compact-sm"
          leftSection={<IconDatabaseImport size={14} />}
          loading={backfill.isPending}
          onClick={() => run(400)}
        >
          Backfill 2 years
        </Button>
      </Group>
    </Alert>
  );
}
