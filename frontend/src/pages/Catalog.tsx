import { useState } from "react";
import { Alert, Button, Pagination, Stack, TextField } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
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
const config: Record<string, { title: string; fields: Field[] }> = {
  directions: {
    title: "ИТ-направления",
    fields: [
      { key: "name", label: "Название", required: true },
      { key: "description", label: "Описание", type: "textarea" },
    ],
  },
  programs: {
    title: "ИТ-программы",
    fields: [
      { key: "name", label: "Название", required: true },
      {
        key: "direction_id",
        label: "Направление",
        type: "number",
        required: true,
      },
      { key: "description", label: "Описание", type: "textarea" },
    ],
  },
  products: {
    title: "ИТ-продукты",
    fields: [
      { key: "name", label: "Название", required: true },
      { key: "vendor", label: "Вендор", required: true },
      { key: "description", label: "Описание", type: "textarea" },
    ],
  },
  users: {
    title: "Пользователи",
    fields: [
      { key: "full_name", label: "ФИО", required: true },
      { key: "email", label: "Email", required: true },
      {
        key: "keycloak_user_id",
        label: "Keycloak subject (ID пользователя)",
        required: true,
      },
      {
        key: "role",
        label: "Роль",
        options: ["user", "manager", "admin"].map((id) => ({ id, name: id })),
      },
      { key: "manager_id", label: "Руководитель", type: "number" },
      { key: "active", label: "Активен", type: "boolean" },
    ],
  },
};
export default function Catalog({ kind }: { kind: string }) {
  const { user } = useAuth();
  const c = config[kind];
  const [q, setQ] = useState(""),
    [page, setPage] = useState(1),
    [edit, setEdit] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [success, setSuccess] = useState("");
  const qc = useQueryClient();
  const data = useData(`/${kind}`, { q, page, page_size: 20 });
  const dirs = useData("/directions", { page_size: 1000 }),
    users = useData("/users", { page_size: 1000 });
  const fields = c.fields.map((f) =>
    f.key === "direction_id"
      ? { ...f, options: dirs.data?.items ?? [] }
      : f.key === "manager_id"
        ? {
            ...f,
            options: (users.data?.items ?? [])
              .filter((u: Row) => u.role !== "user")
              .map((u: Row) => ({ id: u.id, name: u.full_name })),
          }
        : { ...f, disabled: f.key === "keycloak_user_id" && !!edit?.id },
  );
  return (
    <>
      <Title
        action={
          user.role === "admin" && (
            <Button
              variant="contained"
              onClick={() =>
                setEdit(
                  kind === "users"
                    ? { role: "user", active: true }
                    : { name: "", description: "" },
                )
              }
            >
              Добавить
            </Button>
          )
        }
      >
        {c.title}
      </Title>
      {kind === "users" && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Создание учётной записи и пароли — в Keycloak. Здесь задаются права
          CRM, руководитель и доступ. Роль CRM проверяется при каждом запросе.
        </Alert>
      )}
      {error && <Alert severity="error">{error}</Alert>}
      {success && (
        <Alert severity="success" onClose={() => setSuccess("")}>
          {success}
        </Alert>
      )}
      <TextField
        label="Поиск"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setPage(1);
        }}
        sx={{ mb: 2 }}
      />
      <State query={data}>
        <DataTable
          rows={data.data?.items ?? []}
          columns={Object.fromEntries(
            c.fields
              .filter((f) => f.key !== "keycloak_user_id")
              .map((f) => [f.key, f.label]),
          )}
          onRow={user.role === "admin" ? setEdit : undefined}
        />
        <Pagination
          sx={{ my: 2 }}
          page={page}
          count={Math.ceil((data.data?.total ?? 0) / 20)}
          onChange={(_, p) => setPage(p)}
        />
      </State>
      {edit && (
        <>
          <Editor
            title={edit.id ? "Редактирование" : "Новая запись"}
            fields={fields}
            initial={Object.fromEntries(
              c.fields.map((f) => [
                f.key,
                edit[f.key] ??
                  (f.type === "boolean"
                    ? true
                    : f.key === "manager_id"
                      ? null
                      : ""),
              ]),
            )}
            onClose={() => setEdit(null)}
            onSave={async (v) => {
              await api.request({
                url: `/${kind}${edit.id ? "/" + edit.id : ""}`,
                method: edit.id ? "PUT" : "POST",
                data: v,
              });
              setSuccess("Изменения сохранены");
            }}
          />
          {edit.id && kind !== "users" && (
            <Stack position="fixed" bottom={16} right={16} zIndex={1400}>
              <Button
                color="error"
                variant="contained"
                onClick={async () => {
                  if (
                    !confirm(
                      "Удалить запись? Связанные записи препятствуют удалению.",
                    )
                  )
                    return;
                  try {
                    await api.delete(`/${kind}/${edit.id}`);
                    setEdit(null);
                    await qc.invalidateQueries();
                    setSuccess("Запись удалена");
                  } catch (e) {
                    setError(message(e));
                    setEdit(null);
                  }
                }}
              >
                Удалить запись
              </Button>
            </Stack>
          )}
        </>
      )}
    </>
  );
}
