import { useState } from "react";
import {
  useNavigate,
  useParams,
  useSearchParams,
  Link,
} from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Pagination,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { api, download, message } from "../api/client";
import { useAuth } from "../auth/Auth";
import { Filters } from "../components/Filters";
import {
  DataTable,
  Editor,
  State,
  Title,
  useData,
  type Row,
  type Field,
} from "../components/common";
const inputKeys = [
  "university_id",
  "program_id",
  "product_id",
  "responsible_employee_id",
  "workflow_id",
  "contract_number",
  "license_signed",
  "license_start_date",
  "license_end_date",
  "transfer_status",
  "notes",
  "applications",
  "students",
  "streams",
];
function InteractionEditor({
  item,
  onClose,
}: {
  item: Row;
  onClose: () => void;
}) {
  const uni = useData("/universities", { page_size: 1000 }),
    progs = useData("/programs", { page_size: 1000 }),
    products = useData("/products", { page_size: 1000 }),
    users = useData("/users", { page_size: 1000 }),
    wfs = useData("/workflows");
  const fields: Field[] = [
    ...(
      [
        ["university_id", "ВУЗ", uni.data?.items],
        ["program_id", "Программа", progs.data?.items],
        ["product_id", "Продукт", products.data?.items],
        [
          "responsible_employee_id",
          "Ответственный",
          users.data?.items?.map((u: Row) => ({ id: u.id, name: u.full_name })),
        ],
        ["workflow_id", "Workflow", wfs.data?.filter((w: Row) => w.active)],
      ] as [string, string, Row[]][]
    ).map(([key, label, options]) => ({
      key,
      label,
      type: "number",
      options: (options ?? []).map((o) => ({ id: o.id, name: o.name })),
      required: key !== "responsible_employee_id",
      disabled: !!item.id && ["university_id", "workflow_id"].includes(key),
    })),
    { key: "contract_number", label: "Номер договора" },
    { key: "license_signed", label: "Лицензия подписана", type: "boolean" },
    { key: "license_start_date", label: "Начало лицензии", type: "date" },
    { key: "license_end_date", label: "Окончание лицензии", type: "date" },
    { key: "transfer_status", label: "Статус передачи" },
    { key: "notes", label: "Комментарий", type: "textarea" },
    ...["applications", "students", "streams"].map((key, i) => ({
      key,
      label: ["Заявки", "Обучающиеся", "Потоки"][i],
      type: "number",
    })),
  ];
  return (
    <Editor
      title={item.id ? "Редактировать взаимодействие" : "Новое взаимодействие"}
      fields={fields}
      initial={Object.fromEntries(
        inputKeys.map((k) => [
          k,
          item[k] ??
            (["applications", "students", "streams"].includes(k)
              ? 0
              : k === "license_signed"
                ? false
                : [
                      "license_start_date",
                      "license_end_date",
                      "responsible_employee_id",
                    ].includes(k)
                  ? null
                  : k === "transfer_status"
                    ? "В работе"
                    : ""),
        ]),
      )}
      onClose={onClose}
      onSave={(v) =>
        api.request({
          url: `/interactions${item.id ? "/" + item.id : ""}`,
          method: item.id ? "PUT" : "POST",
          params: item.id ? { version: item.version } : undefined,
          data: v,
        })
      }
    />
  );
}
export default function Interactions() {
  const [search] = useSearchParams();
  const [filters, setFilters] = useState<Row>({
    university_id: search.get("university_id")
      ? Number(search.get("university_id"))
      : undefined,
  });
  const [page, setPage] = useState(1),
    [edit, setEdit] = useState(false);
  const nav = useNavigate();
  const query = useData("/interactions", { ...filters, page, page_size: 20 });
  return (
    <>
      <Title
        action={
          <Button variant="contained" onClick={() => setEdit(true)}>
            Создать
          </Button>
        }
      >
        Взаимодействия
      </Title>
      <Filters
        value={filters}
        onChange={(v) => {
          setFilters(v);
          setPage(1);
        }}
      />
      <TextField
        label="Поиск по ВУЗу, программе, продукту, договору"
        fullWidth
        value={filters.q ?? ""}
        onChange={(e) => {
          setFilters({ ...filters, q: e.target.value });
          setPage(1);
        }}
        sx={{ mb: 2 }}
      />
      <State query={query}>
        <DataTable
          rows={query.data?.items ?? []}
          columns={{
            university: "ВУЗ",
            program: "Программа",
            product: "Продукт",
            stage: "Этап",
            responsible: "Ответственный",
            contract_number: "Договор",
          }}
          onRow={(r) => nav(`/interactions/${r.id}`)}
        />
        <Pagination
          sx={{ mt: 2 }}
          page={page}
          count={Math.ceil((query.data?.total ?? 0) / 20)}
          onChange={(_, v) => setPage(v)}
        />
      </State>
      {edit && (
        <InteractionEditor
          item={{ university_id: filters.university_id, workflow_id: 1 }}
          onClose={() => setEdit(false)}
        />
      )}
    </>
  );
}
export function InteractionDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const path = `/interactions/${id}`;
  const query = useData(path),
    allowed = useData(`${path}/allowed-stages`),
    wfs = useData("/workflows"),
    timeline = useData(`${path}/timeline`),
    comments = useData(`${path}/comments`),
    files = useData(`${path}/attachments`),
    advice = useData(`${path}/advice`);
  const qc = useQueryClient();
  const [edit, setEdit] = useState(false),
    [transition, setTransition] = useState(false),
    [stage, setStage] = useState(""),
    [note, setNote] = useState(""),
    [comment, setComment] = useState(""),
    [upload, setUpload] = useState<File | null>(null),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [busy, setBusy] = useState(false);
  const i = query.data;
  const stages =
    wfs.data?.find((w: Row) => w.id === i?.workflow_id)?.stages ?? [];
  async function act(fn: () => Promise<unknown>, text = "Изменения сохранены") {
    setBusy(true);
    setError("");
    try {
      await fn();
      await qc.invalidateQueries();
      setSuccess(text);
    } catch (e) {
      setError(message(e));
      await qc.invalidateQueries();
    } finally {
      setBusy(false);
    }
  }
  async function sendFile(file: File, stageId: number) {
    const data = new FormData();
    data.append("file", file);
    data.append("stage_id", String(stageId));
    await api.post(`${path}/attachments`, data);
  }
  return (
    <State query={query}>
      {i && (
        <>
          <Title
            action={
              <Button onClick={() => setEdit(true)}>Редактировать</Button>
            }
          >
            {i.program}
          </Title>
          <Typography variant="h6" mb={2}>
            <Link to={`/universities/${i.university_id}`}>{i.university}</Link>{" "}
            · {i.product}
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          {success && (
            <Alert
              severity="success"
              sx={{ mb: 2 }}
              onClose={() => setSuccess("")}
            >
              {success}
            </Alert>
          )}
          <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
            <Box className="cards">
              {[
                ["Ответственный", i.responsible],
                ["Договор", i.contract_number],
                ["Лицензия", i.license_signed ? "Подписана" : "Не подписана"],
                [
                  "Срок",
                  `${i.license_start_date ?? "—"} → ${i.license_end_date ?? "—"}`,
                ],
                ["Передача", i.transfer_status],
                [
                  "Заявки / студенты / потоки",
                  `${i.applications} / ${i.students} / ${i.streams}`,
                ],
              ].map(([k, v]) => (
                <Box key={k}>
                  <Typography color="text.secondary">{k}</Typography>
                  <Typography>{v || "—"}</Typography>
                </Box>
              ))}
            </Box>
            <Typography mt={2}>{i.notes}</Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
              mb={3}
            >
              <Typography variant="h5">Workflow</Typography>
              <Button
                variant="contained"
                disabled={!allowed.data?.length}
                onClick={() => {
                  setStage(String(allowed.data?.[0]?.id ?? ""));
                  setTransition(true);
                }}
              >
                Изменить этап
              </Button>
            </Stack>
            <Stepper
              activeStep={stages.findIndex(
                (s: Row) => s.id === i.current_workflow_stage_id,
              )}
              orientation="vertical"
            >
              {stages.map((s: Row) => (
                <Step key={s.id}>
                  <StepLabel
                    optional={
                      <Typography variant="caption">
                        {!s.active
                          ? "Отключён"
                          : s.optional
                            ? "Необязательный этап"
                            : ""}
                      </Typography>
                    }
                  >
                    {s.name}
                  </StepLabel>
                </Step>
              ))}
            </Stepper>
          </Paper>
          <Alert severity="info" sx={{ mb: 3 }}>
            <strong>Рекомендации помощника</strong>
            {advice.data?.suggestions?.map((s: string) => (
              <Typography key={s}>{s}</Typography>
            ))}
          </Alert>
          <Box className="charts">
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Typography variant="h5" mb={3}>
                История переходов
              </Typography>
              {(timeline.data ?? []).map((t: Row) => (
                <Box
                  key={t.id}
                  sx={{ borderLeft: "3px solid #6534b5", pl: 2, pb: 3 }}
                >
                  <Typography variant="caption">
                    {new Date(t.created_at).toLocaleString("ru")} · {t.actor}
                  </Typography>
                  <Typography fontWeight={600}>
                    {t.from_stage ?? "Начало"} → {t.to_stage}
                  </Typography>
                  <Typography>{t.comment}</Typography>
                </Box>
              ))}
            </Paper>
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Typography variant="h5" mb={3}>
                Комментарии
              </Typography>
              {(comments.data ?? []).map((c: Row) => (
                <Box key={c.id} mb={2}>
                  <Typography variant="caption">
                    {c.actor} · {new Date(c.created_at).toLocaleString("ru")}
                  </Typography>
                  <Typography sx={{ whiteSpace: "pre-wrap" }}>
                    {c.text}
                  </Typography>
                </Box>
              ))}
              <TextField
                label="Комментарий к текущему этапу"
                multiline
                rows={3}
                fullWidth
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <Button
                disabled={busy || !comment.trim()}
                sx={{ mt: 2 }}
                onClick={() =>
                  act(async () => {
                    await api.post(`${path}/comments`, {
                      stage_id: i.current_workflow_stage_id,
                      text: comment,
                    });
                    setComment("");
                  }, "Комментарий добавлен")
                }
              >
                Отправить
              </Button>
              <Typography variant="h5" mt={4} mb={2}>
                Вложения
              </Typography>
              {(files.data ?? []).map((f: Row) => (
                <Button
                  key={f.id}
                  fullWidth
                  sx={{ justifyContent: "start" }}
                  onClick={() =>
                    act(
                      () =>
                        download(
                          `/attachments/${f.id}/download`,
                          f.original_filename,
                        ),
                      "Файл скачан",
                    )
                  }
                >
                  {f.original_filename} · {Math.ceil(f.size / 1024)} КБ
                </Button>
              ))}
              <Button component="label" disabled={busy}>
                Загрузить файл
                <input
                  hidden
                  type="file"
                  accept=".png,.jpg,.jpeg,.pdf,.zip,.gz,.gzip,.rar,.doc,.docx,.xls,.xlsx"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f)
                      void act(
                        () => sendFile(f, i.current_workflow_stage_id),
                        "Файл загружен",
                      );
                    e.target.value = "";
                  }}
                />
              </Button>
            </Paper>
          </Box>
          {edit && (
            <InteractionEditor item={i} onClose={() => setEdit(false)} />
          )}
          <Dialog
            open={transition}
            onClose={() => !busy && setTransition(false)}
            fullWidth
          >
            <DialogTitle>Переход на этап</DialogTitle>
            <DialogContent>
              <Stack gap={3} pt={1}>
                <TextField
                  select
                  label="Новый этап"
                  value={stage}
                  onChange={(e) => setStage(e.target.value)}
                >
                  {allowed.data?.map((s: Row) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Комментарий"
                  multiline
                  rows={3}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
                <Button component="label">
                  {upload?.name ?? "Прикрепить файл"}
                  <input
                    hidden
                    type="file"
                    onChange={(e) => setUpload(e.target.files?.[0] ?? null)}
                  />
                </Button>
                {error && <Alert severity="error">{error}</Alert>}
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button disabled={busy} onClick={() => setTransition(false)}>
                Отмена
              </Button>
              <Button
                variant="contained"
                disabled={busy || !stage}
                onClick={() =>
                  act(async () => {
                    await api.post(`${path}/transition`, {
                      to_stage_id: Number(stage),
                      version: i.version,
                      comment: note,
                    });
                    setTransition(false);
                    setNote("");
                    if (upload) {
                      try {
                        await sendFile(upload, Number(stage));
                        setUpload(null);
                      } catch (e) {
                        throw new Error(
                          "Этап изменён, но файл не загружен: " +
                            message(e) +
                            ". Загрузите его в разделе вложений.",
                        );
                      }
                    }
                  }, "Этап изменён")
                }
              >
                Подтвердить
              </Button>
            </DialogActions>
          </Dialog>
          {user.role === "admin" && (
            <Button
              color="error"
              sx={{ mt: 4 }}
              onClick={() => {
                if (
                  confirm(
                    "Удалить взаимодействие, комментарии, историю и вложения?",
                  )
                )
                  void act(async () => {
                    await api.delete(path);
                    nav("/interactions");
                  });
              }}
            >
              Удалить взаимодействие
            </Button>
          )}
        </>
      )}
    </State>
  );
}
