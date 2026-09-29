import { useState } from "react";
import {
  Alert,
  Button,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { api, download, message } from "../api/client";
import { DataTable, Title, useData, type Row } from "../components/common";
const fields: Record<string, string> = {
  university: "Название ВУЗа",
  vendor: "Вендор",
  product: "ПО",
  contract_number: "Номер договора",
  license_signed: "Подписание лицензии",
  license_end_date: "Срок действия лицензии",
  transfer_status: "Статус по передаче",
  responsible: "ФИО Менеджера",
  university_contact: "Ответственные от ВУЗа",
  notes: "Комментарий",
  direction: "ИТ-направление",
  program: "ИТ-программа",
  applications: "Заявки",
  students: "Обучающиеся",
  streams: "Потоки",
};
export default function Import() {
  const [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState<Row | null>(null),
    [mapping, setMapping] = useState<Record<string, string>>({}),
    [program, setProgram] = useState(""),
    [workflow, setWorkflow] = useState("1"),
    [result, setResult] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const programs = useData("/programs", { page_size: 1000 }),
    workflows = useData("/workflows");
  const qc = useQueryClient();
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
      <Title>Импорт Excel</Title>
      <Alert severity="info" sx={{ mb: 3 }}>
        Загрузите XLS или XLSX, сопоставьте колонки и проверьте строки.
        Совпадение ВУЗа, программы, продукта и номера договора обновляет
        существующее взаимодействие. Новые ВУЗы может создавать администратор.
      </Alert>
      <Stack direction="row" gap={2} mb={3}>
        <Button variant="contained" component="label" disabled={busy}>
          Выбрать Excel
          <input
            hidden
            type="file"
            accept=".xls,.xlsx"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              setFile(f);
              setResult(null);
              setPreview(null);
              void act(async () => {
                const data = new FormData();
                data.append("file", f);
                const p = (await api.post("/import/preview", data)).data;
                setPreview(p);
                setMapping(
                  Object.fromEntries(
                    Object.entries(fields)
                      .filter(([, label]) => p.headers.includes(label))
                      .map(([key, label]) => [key, label]),
                  ),
                );
              });
              e.target.value = "";
            }}
          />
        </Button>
        <Button
          onClick={() =>
            act(() => download("/import/template", "import-template.xlsx"))
          }
        >
          Скачать шаблон
        </Button>
      </Stack>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {preview && (
        <>
          <Typography variant="h6">
            {file?.name} · {preview.total} строк
          </Typography>
          <Paper variant="outlined" sx={{ p: 3, my: 3 }}>
            <Typography mb={2}>
              Сопоставление колонок Excel с полями CRM
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={2}>
              {Object.entries(fields).map(([key, label]) => (
                <TextField
                  key={key}
                  select
                  label={label}
                  value={mapping[key] ?? ""}
                  sx={{ width: 240 }}
                  onChange={(e) =>
                    setMapping({ ...mapping, [key]: e.target.value })
                  }
                >
                  <MenuItem value="">Не импортировать</MenuItem>
                  {preview.headers.map((h: string) => (
                    <MenuItem key={h} value={h}>
                      {h}
                    </MenuItem>
                  ))}
                </TextField>
              ))}
            </Stack>
            <Stack direction="row" flexWrap="wrap" gap={2} mt={3}>
              <TextField
                select
                label="Программа по умолчанию"
                sx={{ minWidth: 260 }}
                value={program}
                onChange={(e) => setProgram(e.target.value)}
              >
                <MenuItem value="">Из колонки Excel</MenuItem>
                {programs.data?.items.map((p: Row) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Workflow для новых записей"
                value={workflow}
                onChange={(e) => setWorkflow(e.target.value)}
                sx={{ minWidth: 260 }}
              >
                {workflows.data
                  ?.filter((w: Row) => w.active)
                  .map((w: Row) => (
                    <MenuItem key={w.id} value={w.id}>
                      {w.name}
                    </MenuItem>
                  ))}
              </TextField>
            </Stack>
          </Paper>
          <Typography variant="h6" mb={2}>
            Предпросмотр выбранного сопоставления
          </Typography>
          <DataTable
            rows={preview.rows.map((r: Row) =>
              Object.fromEntries(
                Object.entries(mapping)
                  .filter(([, col]) => col)
                  .map(([key, col]) => [key, r[col]]),
              ),
            )}
            columns={Object.fromEntries(
              Object.keys(mapping)
                .filter((k) => mapping[k])
                .map((k) => [k, fields[k]]),
            )}
          />
          <Button
            sx={{ my: 3 }}
            variant="contained"
            disabled={
              busy || !mapping.university || !mapping.product || !!result
            }
            onClick={() => {
              if (!confirm(`Импортировать ${preview.total} строк?`)) return;
              void act(async () => {
                const data = new FormData();
                data.append("file", file!);
                data.append(
                  "mapping",
                  JSON.stringify(
                    Object.fromEntries(
                      Object.entries(mapping).filter(([, v]) => v),
                    ),
                  ),
                );
                data.append("workflow_id", workflow);
                if (program) data.append("default_program_id", program);
                setResult((await api.post("/import/commit", data)).data);
                await qc.invalidateQueries();
              });
            }}
          >
            Подтвердить импорт
          </Button>
        </>
      )}
      {result && (
        <>
          <Alert severity={result.errors.length ? "warning" : "success"}>
            Создано: {result.created} · Обновлено: {result.updated} · Пропущено:{" "}
            {result.skipped}
          </Alert>
          {result.errors.length > 0 && (
            <DataTable
              rows={result.errors}
              columns={{ row: "Строка", message: "Ошибка" }}
            />
          )}
        </>
      )}
    </>
  );
}
