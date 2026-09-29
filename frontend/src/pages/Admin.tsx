import { useState } from "react";
import {
  Alert,
  Button,
  Pagination,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { api, message } from "../api/client";
import {
  DataTable,
  Editor,
  State,
  Title,
  useData,
  type Row,
} from "../components/common";
export function Settings() {
  const query = useData("/settings");
  const [edit, setEdit] = useState(false);
  return (
    <>
      <Title>Настройки системы</Title>
      <State query={query}>
        {query.data && (
          <Paper sx={{ p: 3 }} variant="outlined">
            <Typography variant="h6">{query.data.organization}</Typography>
            <Typography my={2}>
              Регламент хранения: {query.data.retention_days} дней
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              Автоматическое удаление документов по сроку отключено. Политику
              хранения согласует заказчик. Размер файлов, CORS и адреса
              интеграций задаются переменными окружения.
            </Alert>
            <Button onClick={() => setEdit(true)}>Изменить</Button>
          </Paper>
        )}
      </State>
      {edit && (
        <Editor
          title="Настройки"
          initial={query.data}
          fields={[
            { key: "organization", label: "Организация", required: true },
            {
              key: "retention_days",
              label: "Срок хранения, дней",
              type: "number",
              required: true,
            },
          ]}
          onSave={(v) => api.put("/settings", v)}
          onClose={() => setEdit(false)}
        />
      )}
    </>
  );
}
export function Audit() {
  const [page, setPage] = useState(1),
    [action, setAction] = useState("");
  const query = useData("/audit", { page, action, page_size: 20 });
  return (
    <>
      <Title>Журнал аудита</Title>
      <TextField
        label="Фильтр по действию"
        value={action}
        onChange={(e) => {
          setAction(e.target.value);
          setPage(1);
        }}
        sx={{ mb: 2 }}
      />
      <State query={query}>
        <DataTable
          rows={query.data?.items ?? []}
          columns={{
            created_at: "Дата",
            user_id: "Пользователь",
            action: "Действие",
            entity_type: "Сущность",
            entity_id: "ID",
            old_value: "До",
            new_value: "После",
          }}
        />
        <Pagination
          page={page}
          count={Math.ceil((query.data?.total ?? 0) / 20)}
          onChange={(_, v) => setPage(v)}
          sx={{ mt: 2 }}
        />
      </State>
    </>
  );
}
export function Integrations() {
  const query = useData("/integrations");
  const qc = useQueryClient();
  const [result, setResult] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <>
      <Title>Интеграции</Title>
      <Alert severity="info" sx={{ mb: 3 }}>
        Демонстрационные адаптеры предоставляют стабильный JSON-контракт.
        Повторная синхронизация обновляет записи по внешнему ID. Реальные
        сервисы подключаются через HTTP-адаптер и параметры окружения.
      </Alert>
      <State query={query}>
        <Stack gap={3}>
          {["lms", "website"].map((source) => (
            <Paper key={source} variant="outlined" sx={{ p: 3 }}>
              <Typography variant="h5">
                {source === "lms" ? "Учебная платформа LMS" : "Сайт ИТ Школы"}
              </Typography>
              <Typography
                component="pre"
                sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
              >
                {JSON.stringify(query.data?.[source], null, 2)}
              </Typography>
              <Button
                disabled={busy}
                variant="contained"
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    setResult(
                      (await api.post(`/integrations/${source}/sync`)).data,
                    );
                    await qc.invalidateQueries();
                  } catch (e) {
                    setError(message(e));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Синхронизировать
              </Button>
            </Paper>
          ))}
        </Stack>
      </State>
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
      {result && (
        <>
          <Alert
            severity={result.errors.length ? "warning" : "success"}
            sx={{ mt: 2 }}
          >
            Создано {result.created}, обновлено {result.updated}, пропущено{" "}
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
export function Help() {
  return (
    <>
      <Title>Руководство пользователя</Title>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h6">1. Найдите ВУЗ</Typography>
        <Typography mb={3}>
          Откройте «ВУЗы», задайте поиск или фильтры. Карточка содержит контакты
          и взаимодействия. Нажмите на строку взаимодействия для открытия
          workflow.
        </Typography>
        <Typography variant="h6">2. Ведите взаимодействие</Typography>
        <Typography mb={3}>
          В карточке доступны договор, лицензия, показатели обучения,
          комментарии, вложения и история переходов. Кнопка «Изменить этап»
          показывает разрешённые переходы для вашей роли.
        </Typography>
        <Typography variant="h6">3. Получите статистику</Typography>
        <Typography mb={3}>
          Dashboard строится по доступным вам данным. Выберите период,
          программу, продукт или ответственного. В «Отчётах» выберите колонки,
          проверьте preview и скачайте XLSX, XLS, PDF или JSON.
        </Typography>
        <Typography variant="h6">4. Импортируйте данные</Typography>
        <Typography mb={3}>
          Руководитель или администратор загружает Excel, сопоставляет колонки и
          подтверждает импорт. Результат показывает созданные, обновлённые и
          пропущенные строки с ошибками.
        </Typography>
        <Typography variant="h6">5. Администрирование</Typography>
        <Typography>
          Администратор управляет справочниками, ролями CRM, настройками и
          этапами workflow. Учётные записи и пароли обслуживает Keycloak. Журнал
          аудита фиксирует изменения.
        </Typography>
        <Button href="/handbook/USER_GUIDE.pdf" target="_blank" sx={{ mt: 3 }}>
          Скачать руководство PDF
        </Button>
        <Button href="/handbook/" target="_blank" sx={{ mt: 3 }}>
          Вся документация со скриншотами
        </Button>
      </Paper>
    </>
  );
}
