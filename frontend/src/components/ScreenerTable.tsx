import {
  Alert,
  Group,
  Loader,
  Table,
  Text,
  TextInput,
  UnstyledButton,
} from "@mantine/core";
import {
  IconSearch,
  IconSelector,
  IconSortAscending,
  IconSortDescending,
} from "@tabler/icons-react";
import {
  createColumnHelper,
  createCoreRowModel,
  createFilteredRowModel,
  createSortedRowModel,
  columnFilteringFeature,
  columnVisibilityFeature,
  filterFn_includesString,
  globalFilteringFeature,
  rowSortingFeature,
  sortFn_basic,
  sortFn_text,
  tableFeatures,
  useTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { useScreener } from "../api/queries";
import type { ScreenerRow } from "../api/types";
import { fmtCompact, fmtPct, fmtPrice } from "../theme/format";

const features = tableFeatures({
  columnFilteringFeature,
  columnVisibilityFeature,
  globalFilteringFeature,
  rowSortingFeature,
  coreRowModel: createCoreRowModel(),
  sortedRowModel: createSortedRowModel(),
  filteredRowModel: createFilteredRowModel(),
  sortFns: { text: sortFn_text, basic: sortFn_basic },
  filterFns: { includesString: filterFn_includesString },
});

const col = createColumnHelper<typeof features, ScreenerRow>();

/** Right-aligned numeric cell; colours signed values. */
function Num({ value, tone = false }: { value: string; tone?: boolean }) {
  const negative = value.startsWith("-");
  return (
    <Text
      component="span"
      size="sm"
      className="numeric"
      c={
        tone
          ? negative
            ? "red"
            : value === "—"
              ? "dimmed"
              : "teal"
          : undefined
      }
    >
      {value}
    </Text>
  );
}

const columns: ColumnDef<typeof features, ScreenerRow, any>[] = [
  col.accessor("symbol", {
    header: "Symbol",
    sortFn: "text",
    cell: (c) => (
      <Text size="sm" fw={600}>
        {c.getValue()}
      </Text>
    ),
  }),
  col.accessor("sector", {
    header: "Sector",
    sortFn: "text",
    cell: (c) => (
      <Text size="xs" c="dimmed">
        {c.getValue() ?? "—"}
      </Text>
    ),
  }),
  col.accessor("close", {
    sortFn: "basic",
    sortUndefined: "last",
    header: "Close",
    cell: (c) => <Num value={fmtPrice(c.getValue())} />,
  }),
  col.accessor("change_pct", {
    sortFn: "basic",
    sortUndefined: "last",
    header: "Chg %",
    cell: (c) => <Num value={fmtPct(c.getValue())} tone />,
  }),
  col.accessor("rel_volume", {
    sortFn: "basic",
    sortUndefined: "last",
    header: "Rel Vol",
    cell: (c) => <Num value={c.getValue()?.toFixed(2) ?? "—"} />,
  }),
  col.accessor("return_3m", {
    sortFn: "basic",
    sortUndefined: "last",
    header: "3M %",
    cell: (c) => <Num value={fmtPct(c.getValue())} tone />,
  }),
  col.accessor("return_1y", {
    sortFn: "basic",
    sortUndefined: "last",
    header: "1Y %",
    cell: (c) => <Num value={fmtPct(c.getValue())} tone />,
  }),
  col.accessor("volatility", {
    sortFn: "basic",
    sortUndefined: "last",
    header: "Vol %",
    cell: (c) => <Num value={c.getValue()?.toFixed(1) ?? "—"} />,
  }),
  col.accessor("pe_ratio", {
    sortFn: "basic",
    sortUndefined: "last",
    header: "P/E",
    cell: (c) => <Num value={c.getValue()?.toFixed(1) ?? "—"} />,
  }),
  col.accessor("market_cap", {
    sortFn: "basic",
    sortUndefined: "last",
    header: "Mkt Cap",
    cell: (c) => <Num value={fmtCompact(c.getValue())} />,
  }),
];

type Props = {
  selected: string | null;
  onSelect: (symbol: string) => void;
};

export function ScreenerTable({ selected, onSelect }: Props) {
  const { data, isLoading, error } = useScreener();
  const [sorting, setSorting] = useState<SortingState>([
    { id: "symbol", desc: false },
  ]);
  const [filter, setFilter] = useState("");

  const rows = useMemo(() => data ?? [], [data]);

  const table = useTable<typeof features, ScreenerRow>({
    features,
    data: rows,
    columns,
    globalFilterFn: "includesString",
    state: { sorting, globalFilter: filter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
  });

  if (error) return <Alert color="red">{(error as Error).message}</Alert>;
  if (isLoading)
    return (
      <Group justify="center" py="xl">
        <Loader size="sm" />
      </Group>
    );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        minHeight: 0,
      }}
    >
      <TextInput
        size="xs"
        mb="xs"
        style={{ flex: "0 0 auto" }}
        placeholder="Filter symbols…"
        leftSection={<IconSearch size={14} />}
        value={filter}
        onChange={(e) => setFilter(e.currentTarget.value)}
      />
      {/* Mantine's scroll container only sets overflow-x, so overflow-y is
          declared here; type="native" keeps both axes on one real scrollport.
          minHeight: 0 is required for the flex parent to allow shrinking. */}
      <Table.ScrollContainer
        minWidth={900}
        type="native"
        style={{ flex: 1, minHeight: 0, overflowY: "auto" }}
      >
        <Table highlightOnHover stickyHeader>
          <Table.Thead>
            {table.getHeaderGroups().map((hg) => (
              <Table.Tr key={hg.id}>
                {hg.headers.map((h) => {
                  const sorted = h.column.getIsSorted();
                  const Icon =
                    sorted === "asc"
                      ? IconSortAscending
                      : sorted === "desc"
                        ? IconSortDescending
                        : IconSelector;
                  return (
                    <Table.Th key={h.id}>
                      <UnstyledButton
                        onClick={h.column.getToggleSortingHandler()}
                        style={{ width: "100%" }}
                      >
                        <Group gap={4} wrap="nowrap" justify="flex-start">
                          <Text size="xs" fw={600} tt="uppercase" c="dimmed">
                            {<table.FlexRender header={h} />}
                          </Text>
                          <Icon size={12} opacity={sorted ? 1 : 0.35} />
                        </Group>
                      </UnstyledButton>
                    </Table.Th>
                  );
                })}
              </Table.Tr>
            ))}
          </Table.Thead>
          <Table.Tbody>
            {table.getRowModel().rows.map((row) => (
              <Table.Tr
                key={row.id}
                onClick={() => onSelect(row.original.symbol)}
                bg={
                  row.original.symbol === selected
                    ? "var(--mantine-color-dark-6)"
                    : undefined
                }
                style={{ cursor: "pointer" }}
              >
                {row.getVisibleCells().map((cell) => (
                  <Table.Td key={cell.id}>
                    <table.FlexRender cell={cell} />
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </div>
  );
}
