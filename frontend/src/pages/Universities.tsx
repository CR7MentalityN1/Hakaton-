import { useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  Alert,
  Button,
  MenuItem,
  Pagination,
  Paper,
  Stack,
  TextField,
  Typography,
  Tabs,
  Tab,
  Stepper,
  Step,
  StepLabel,
} from "@mui/material";
import { api, message } from "../api/client";
import { useAuth } from "../auth/Auth";
import {
  DataTable,
  Editor,
  State,
  Title,
  useData,
  type Row,
  type Field,
} from "../components/common";
const fields: Field[] = [
  { key: "name", label: "Название", required: true },
  { key: "short_name", label: "Сокращение" },
  { key: "city", label: "Город", required: true },
  { key: "region", label: "Регион" },
];
export default function Universities() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [q, setQ] = useState(""),
    [city, setCity] = useState(""),
    [region, setRegion] = useState(""),
    [page, setPage] = useState(1),
    [sort, setSort] = useState("name"),
    [edit, setEdit] = useState(false);
  const query = useData("/universities", {
    q,
    city,
    region,
    page,
    sort,
    page_size: 20,
  });
  return (
    <>
      <Title
        action={
          user.role === "admin" && (
            <Button variant="contained" onClick={() => setEdit(true)}>
              Добавить ВУЗ
            </Button>
          )
        }
      >
        ВУЗы
      </Title>
      <Stack direction="row" gap={2} mb={2} flexWrap="wrap">
        {[
          [q, setQ, "Поиск"],
          [city, setCity, "Город"],
          [region, setRegion, "Регион"],
        ].map(([v, set, label]) => (
          <TextField
            key={String(label)}
            label={String(label)}
            value={v}
            onChange={(e) => {
              (set as (v: string) => void)(e.target.value);
              setPage(1);
            }}
          />
        ))}
        <TextField
          select
          label="Сортировка"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          {[
            ["name", "Название"],
            ["city", "Город"],
            ["updated_at", "Дата изменения"],
          ].map(([v, n]) => (
            <MenuItem value={v} key={v}>
              {n}
            </MenuItem>
          ))}
        </TextField>
      </Stack>
      <State query={query}>
        <DataTable
          rows={(query.data?.items ?? []).map((r: Row) => ({
            ...r,
            managers: r.managers.map((u: Row) => u.full_name).join(", "),
            statuses: r.statuses.join("; "),
            updated_at: new Date(r.updated_at).toLocaleDateString("ru"),
          }))}
          columns={{
            name: "ВУЗ",
            city: "Город",
            region: "Регион",
            managers: "Ответственные",
            program_count: "Программы",
            product_count: "Продукты",
            statuses: "Этапы",
            updated_at: "Обновлён",
          }}
          onRow={(r) => nav(`/universities/${r.id}`)}
        />
        <Pagination
          sx={{ mt: 2 }}
          page={page}
          count={Math.ceil((query.data?.total ?? 0) / 20)}
          onChange={(_, v) => setPage(v)}
        />
      </State>
      {edit && (
        <Editor
          title="Новый ВУЗ"
          fields={fields}
          initial={{ name: "", short_name: "", city: "", region: "" }}
          onClose={() => setEdit(false)}
          onSave={(v) => api.post("/universities", v)}
        />
      )}
    </>
  );
}
export function UniversityDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const path = `/universities/${id}`;
  const query = useData(path),
    contacts = useData(`${path}/contacts`),
    interactions = useData("/interactions", {
      university_id: id,
      page_size: 1000,
    }),
    users = useData("/users", { page_size: 1000 }),
    workflows = useData("/workflows");
  const [tab, setTab] = useState(0);
  const [edit, setEdit] = useState(""),
    [contact, setContact] = useState<Row>({}),
    [error, setError] = useState("");
  const u = query.data;
  return (
    <State query={query}>
      {u && (
        <>
          <Title
            action={
              user.role === "admin" && (
                <Button onClick={() => setEdit("university")}>
                  Редактировать
                </Button>
              )
            }
          >
            {u.short_name || u.name}
          </Title>
          <Typography variant="h6">{u.name}</Typography>
          <Typography color="text.secondary" mb={3}>
            {u.city} · {u.region}
          </Typography>
          <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">Ответственные сотрудники</Typography>
            <Typography my={2}>
              {u.managers.map((m: Row) => m.full_name).join(", ") ||
                "Не назначены"}
            </Typography>
            {user.role !== "user" && (
              <Button onClick={() => setEdit("assignment")}>
                Назначить / сменить / снять
              </Button>
            )}
          </Paper>
          <Title
            action={
              <Button
                onClick={() => {
                  setContact({
                    full_name: "",
                    position: "",
                    email: "",
                    phone: "",
                  });
                  setEdit("contact");
                }}
              >
                Добавить контакт
              </Button>
            }
          >
            Контакты ВУЗа
          </Title>
          <DataTable
            rows={contacts.data ?? []}
            columns={{
              full_name: "ФИО",
              position: "Должность",
              email: "Email",
              phone: "Телефон",
            }}
            onRow={(r) => {
              setContact(r);
              setEdit("contact");
            }}
          />
          <Typography variant="h5" mt={4} mb={2}>
            Программы, продукты, договоры и workflow
          </Typography>
          <Tabs
            value={tab}
            onChange={(_, value) => setTab(value)}
            sx={{ mb: 2 }}
          >
            <Tab label="Взаимодействия" />
            <Tab label="Workflow" />
          </Tabs>
          <Button
            component={Link}
            to={`/interactions?university_id=${id}`}
            sx={{ mb: 2 }}
          >
            Открыть взаимодействия ВУЗа
          </Button>
          {tab === 0 ? (
            <DataTable
              rows={interactions.data?.items ?? []}
              columns={{
                program: "Программа",
                product: "Продукт",
                contract_number: "Договор",
                license_signed: "Подписана лицензия",
                license_end_date: "Срок лицензии",
                stage: "Workflow",
                responsible: "Ответственный",
              }}
              onRow={(r) => nav(`/interactions/${r.id}`)}
            />
          ) : (
            (interactions.data?.items ?? []).map((item: Row) => {
              const stages =
                workflows.data?.find((w: Row) => w.id === item.workflow_id)
                  ?.stages ?? [];
              return (
                <Paper variant="outlined" sx={{ p: 3, mb: 2 }} key={item.id}>
                  <Typography variant="h6">
                    {item.program} · {item.product}
                  </Typography>
                  <Stepper
                    orientation="vertical"
                    activeStep={stages.findIndex(
                      (s: Row) => s.id === item.current_workflow_stage_id,
                    )}
                    sx={{ my: 2 }}
                  >
                    {stages.map((s: Row) => (
                      <Step key={s.id}>
                        <StepLabel>{s.name}</StepLabel>
                      </Step>
                    ))}
                  </Stepper>
                  <Button component={Link} to={`/interactions/${item.id}`}>
                    Перейти к этапам, комментариям и файлам
                  </Button>
                </Paper>
              );
            })
          )}
          {error && <Alert severity="error">{error}</Alert>}
          {edit === "university" && (
            <Editor
              title="Редактировать ВУЗ"
              fields={fields}
              initial={Object.fromEntries(fields.map((f) => [f.key, u[f.key]]))}
              onClose={() => setEdit("")}
              onSave={(v) => api.put(path, v)}
            />
          )}{" "}
          {edit === "assignment" && (
            <Editor
              title="Ответственный за ВУЗ"
              fields={[
                {
                  key: "employee_id",
                  label: "Сотрудник (пусто — снять назначения)",
                  type: "number",
                  options: (users.data?.items ?? []).map((u: Row) => ({
                    id: u.id,
                    name: u.full_name,
                  })),
                },
              ]}
              initial={{ employee_id: u.managers[0]?.id ?? null }}
              onClose={() => setEdit("")}
              onSave={(v) =>
                api.put(`${path}/assignments`, {
                  employee_ids: v.employee_id ? [v.employee_id] : [],
                })
              }
            />
          )}{" "}
          {edit === "contact" && (
            <Editor
              title="Контакт ВУЗа"
              fields={[
                { key: "full_name", label: "ФИО", required: true },
                { key: "position", label: "Должность" },
                { key: "email", label: "Email" },
                { key: "phone", label: "Телефон" },
              ]}
              initial={Object.fromEntries(
                ["full_name", "position", "email", "phone"].map((k) => [
                  k,
                  contact[k],
                ]),
              )}
              onClose={() => setEdit("")}
              onSave={(v) =>
                api.request({
                  url: `${path}/contacts${contact.id ? "/" + contact.id : ""}`,
                  method: contact.id ? "PUT" : "POST",
                  data: v,
                })
              }
            />
          )}{" "}
          {user.role === "admin" && (
            <Button
              color="error"
              sx={{ mt: 4 }}
              onClick={async () => {
                if (!confirm("Удалить ВУЗ без взаимодействий?")) return;
                try {
                  await api.delete(path);
                  nav("/universities");
                } catch (e) {
                  setError(message(e));
                }
              }}
            >
              Удалить ВУЗ
            </Button>
          )}
        </>
      )}
    </State>
  );
}
