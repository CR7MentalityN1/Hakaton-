import { useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  FormControlLabel,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { api, download, message } from "../api/client";
import { Filters } from "../components/Filters";
import { DataTable, Title, type Row } from "../components/common";
import { columns } from "../features/reports/columns";
export default function Reports() {
  const [filters, setFilters] = useState<Row>({}),
    [selected, setSelected] = useState(Object.keys(columns).slice(0, 8)),
    [preview, setPreview] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Title>Конструктор отчётов</Title>
      <Filters
        value={filters}
        onChange={(v) => {
          setFilters(v);
          setPreview(null);
        }}
      />
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6">Колонки отчёта</Typography>
        {Object.entries(columns).map(([key, label]) => (
          <FormControlLabel
            key={key}
            label={label}
            control={
              <Checkbox
                checked={selected.includes(key)}
                onChange={(e) => {
                  setSelected(
                    e.target.checked
                      ? [...selected, key]
                      : selected.filter((k) => k !== key),
                  );
                  setPreview(null);
                }}
              />
            }
          />
        ))}
        <Stack direction="row" gap={2} flexWrap="wrap" mt={2}>
          <Button
            variant="contained"
            disabled={busy || !selected.length}
            onClick={() =>
              act(async () =>
                setPreview(
                  (
                    await api.post("/reports/preview", {
                      ...filters,
                      columns: selected,
                    })
                  ).data,
                ),
              )
            }
          >
            Предпросмотр
          </Button>
          {["xlsx", "xls", "pdf", "json"].map((format) => (
            <Button
              key={format}
              disabled={busy || !selected.length}
              onClick={() =>
                act(() =>
                  download("/reports/export", `report.${format}`, {
                    ...filters,
                    columns: selected,
                    format,
                  }),
                )
              }
            >
              {format.toUpperCase()}
            </Button>
          ))}
        </Stack>
      </Paper>
      {error && <Alert severity="error">{error}</Alert>}
      {preview && (
        <>
          <Typography mb={2}>
            Найдено записей: {preview.total}. Первые 10 строк:
          </Typography>
          <DataTable rows={preview.items} columns={preview.columns} />
        </>
      )}
    </>
  );
}
