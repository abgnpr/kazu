import { Alert, Badge, Group, Loader, Switch, Table, Text, Tooltip } from "@mantine/core";
import { IconCheck, IconX } from "@tabler/icons-react";
import { useState } from "react";

import { useBreakouts } from "../api/queries";
import type { BreakoutRow } from "../api/types";
import { fmtCompact, fmtPct, fmtPrice } from "../theme/format";

/** Compact pass/fail marker for one of the four conditions. */
function Flag({ ok, label }: { ok: boolean; label: string }) {
  return (
    <Tooltip label={`${label}: ${ok ? "pass" : "fail"}`} withArrow>
      <Text component="span" c={ok ? "teal" : "dimmed"} style={{ display: "inline-flex" }}>
        {ok ? <IconCheck size={13} /> : <IconX size={13} />}
      </Text>
    </Tooltip>
  );
}

function Num({ value, tone = false }: { value: string; tone?: boolean }) {
  const negative = value.startsWith("-");
  return (
    <Text
      component="span"
      size="sm"
      className="numeric"
      c={tone ? (negative ? "red" : value === "—" ? "dimmed" : "teal") : undefined}
    >
      {value}
    </Text>
  );
}

type Props = {
  selected: string | null;
  onSelect: (symbol: string) => void;
};

export function BreakoutTable({ selected, onSelect }: Props) {
  const [onlyPassing, setOnlyPassing] = useState(true);
  const { data, isLoading, error } = useBreakouts(onlyPassing);

  if (error) return <Alert color="red">{(error as Error).message}</Alert>;
  if (isLoading)
    return (
      <Group justify="center" py="xl">
        <Loader size="sm" />
      </Group>
    );

  const rows = data?.rows ?? [];
  const coverage = data?.coverage;

  return (
    <>
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <Text size="xs" tt="uppercase" fw={600} c="dimmed">
            CAR + DMA Breakouts
          </Text>
          <Badge size="xs" variant="light" color={data?.passing ? "teal" : "gray"}>
            {data?.passing ?? 0} passing
          </Badge>
        </Group>
        <Switch
          size="xs"
          label="Only passing"
          checked={onlyPassing}
          onChange={(e) => setOnlyPassing(e.currentTarget.checked)}
        />
      </Group>

      {rows.length === 0 && (
        <Alert variant="light" color="gray" p="xs">
          <Text size="xs">
            {coverage && !coverage.has_200dma
              ? "Not enough history yet — backfill to enable the 200 DMA."
              : onlyPassing
                ? "No stock clears all four conditions today."
                : "No eligible stocks."}
          </Text>
        </Alert>
      )}

      {rows.length > 0 && (
        <Table.ScrollContainer minWidth={1000}>
          <Table highlightOnHover stickyHeader>
            <Table.Thead>
              <Table.Tr>
                {["Symbol", "Close", "Chg %", "30", "50", "200", "CAR", "Cond."].map((h) => (
                  <Table.Th key={h}>
                    <Text size="xs" fw={600} tt="uppercase" c="dimmed">
                      {h}
                    </Text>
                  </Table.Th>
                ))}
                <Table.Th>
                  <Tooltip label="Distance from the 200 DMA — the original ranks by this, ascending">
                    <Text size="xs" fw={600} tt="uppercase" c="dimmed">
                      200 Dist %
                    </Text>
                  </Tooltip>
                </Table.Th>
                {["From 52w High", "Rel Vol", "Volume"].map((h) => (
                  <Table.Th key={h}>
                    <Text size="xs" fw={600} tt="uppercase" c="dimmed">
                      {h}
                    </Text>
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((r: BreakoutRow) => (
                <Table.Tr
                  key={r.symbol}
                  onClick={() => onSelect(r.symbol)}
                  bg={r.symbol === selected ? "var(--mantine-color-dark-6)" : undefined}
                  style={{ cursor: "pointer" }}
                >
                  <Table.Td>
                    <Group gap={6} wrap="nowrap">
                      {r.breakout && (
                        <Tooltip label="Clears all four conditions">
                          <Badge size="xs" circle color="teal" variant="filled" p={0} w={7} h={7} />
                        </Tooltip>
                      )}
                      <Text size="sm" fw={600}>
                        {r.symbol}
                      </Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Num value={fmtPrice(r.close)} />
                  </Table.Td>
                  <Table.Td>
                    <Num value={fmtPct(r.change_pct)} tone />
                  </Table.Td>
                  <Table.Td>
                    <Num value={fmtPrice(r.sma30)} />
                  </Table.Td>
                  <Table.Td>
                    <Num value={fmtPrice(r.sma50)} />
                  </Table.Td>
                  <Table.Td>
                    <Num value={fmtPrice(r.sma200)} />
                  </Table.Td>
                  <Table.Td>
                    <Tooltip
                      label={`CAR rising ${r.car_sessions} session(s) since the 52w high on ${r.high_date}`}
                      withArrow
                    >
                      <Text size="xs" c={r.car_positive ? "teal" : "dimmed"}>
                        {r.car_positive ? "rising" : "flat/falling"}
                      </Text>
                    </Tooltip>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={3} wrap="nowrap">
                      <Flag ok={r.above_30dma} label="Above 30 DMA" />
                      <Flag ok={r.above_50dma} label="Above 50 DMA" />
                      <Flag ok={r.above_200dma} label="Above 200 DMA" />
                      <Flag ok={r.car_positive} label="CAR rising 10 sessions" />
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Num value={fmtPct(r.dist_200dma_pct)} tone />
                  </Table.Td>
                  <Table.Td>
                    <Num value={fmtPct(r.from_52w_high_pct)} tone />
                  </Table.Td>
                  <Table.Td>
                    <Num value={r.rel_volume?.toFixed(2) ?? "—"} />
                  </Table.Td>
                  <Table.Td>
                    <Num value={fmtCompact(r.volume)} />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </>
  );
}
