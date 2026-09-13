import { Badge, Group, Text, Tooltip } from "@mantine/core";

import { useJobs } from "../api/queries";

/** Shows whether the background service's data is current. */
export function StatusBar() {
  const { data, error, isPending } = useJobs();

  // While the query is still retrying, the service is most likely just booting
  // (PyInstaller unpack + DuckDB open). Saying "unreachable" there is alarming
  // and wrong; only report failure once the retries are exhausted.
  if (isPending) {
    return (
      <Badge color="gray" variant="light" size="sm">
        Starting service…
      </Badge>
    );
  }

  if (error) {
    return (
      <Badge color="red" variant="light" size="sm">
        Service unreachable
      </Badge>
    );
  }

  const stale = (data ?? []).filter((j) => j.stale);
  const label = stale.length ? `${stale.length} job(s) stale` : "Data current";

  return (
    <Group gap="xs">
      <Tooltip
        label={(data ?? [])
          .map((j) => `${j.job}: ${j.last_success ?? "never"}`)
          .join("\n")}
        multiline
        withArrow
      >
        <Badge color={stale.length ? "yellow" : "teal"} variant="light" size="sm">
          {label}
        </Badge>
      </Tooltip>
      <Text size="xs" c="dimmed">
        127.0.0.1:8765
      </Text>
    </Group>
  );
}
