import { useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { api, message } from "../api/client";
import { useAuth } from "../auth/Auth";
import { State, Title, useData, type Row } from "../components/common";
export default function Workflows() {
  const { user } = useAuth();
  const query = useData("/workflows");
  const qc = useQueryClient();
  const [edit, setEdit] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const fresh = () => ({
    name: "Новый этап",
    description: "",
    active: true,
    optional: false,
    allowed_roles: ["user", "manager", "admin"],
  });
  function change(index: number, key: string, value: unknown) {
    if (edit)
      setEdit({
        ...edit,
        stages: edit.stages.map((s: Row, i: number) =>
          i === index ? { ...s, [key]: value } : s,
        ),
      });
  }
  return (
    <>
      <Title
        action={
          user.role === "admin" && (
            <Button
              variant="contained"
              onClick={() => {
                setError("");
                setEdit({
                  name: "Новый workflow",
                  description: "",
                  active: true,
                  version: 1,
                  stages: [fresh()],
                });
              }}
            >
              Создать workflow
            </Button>
          )
        }
      >
        Workflow
      </Title>
      <State query={query}>
        {query.data?.map((w: Row) => (
          <Paper variant="outlined" key={w.id} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5">
              {w.name} {!w.active && "· Отключён"}
            </Typography>
            <Typography color="text.secondary" mb={2}>
              {w.description}
            </Typography>
            {w.stages.map((s: Row, i: number) => (
              <Typography
                key={s.id}
                sx={{ opacity: s.active ? 1 : 0.5, py: 0.5 }}
              >
                {i + 1}. {s.name}
                {s.optional ? " · необязательный" : ""}
                {!s.active ? " · отключён" : ""}
              </Typography>
            ))}
            {user.role === "admin" && (
              <Button
                onClick={() => {
                  setEdit(structuredClone(w));
                  setError("");
                }}
              >
                Настроить этапы и права
              </Button>
            )}
          </Paper>
        ))}
      </State>
      {edit && (
        <Dialog
          open
          fullWidth
          maxWidth="md"
          onClose={() => !busy && setEdit(null)}
        >
          <DialogTitle>Конструктор workflow</DialogTitle>
          <DialogContent>
            <Stack gap={2} pt={1}>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField
                label="Название"
                value={edit.name}
                onChange={(e) => setEdit({ ...edit, name: e.target.value })}
              />
              <TextField
                label="Описание"
                value={edit.description}
                onChange={(e) =>
                  setEdit({ ...edit, description: e.target.value })
                }
              />
              <FormControlLabel
                label="Workflow активен"
                control={
                  <Checkbox
                    checked={edit.active}
                    onChange={(e) =>
                      setEdit({ ...edit, active: e.target.checked })
                    }
                  />
                }
              />
              {edit.stages.map((s: Row, i: number) => (
                <Paper
                  key={s.id ?? `new-${i}`}
                  variant="outlined"
                  sx={{ p: 2 }}
                >
                  <Stack gap={2}>
                    <TextField
                      label={`Этап ${i + 1}`}
                      value={s.name}
                      onChange={(e) => change(i, "name", e.target.value)}
                    />
                    <TextField
                      label="Описание этапа"
                      value={s.description}
                      onChange={(e) => change(i, "description", e.target.value)}
                    />
                    <TextField
                      select
                      label="Роли, которым разрешён переход"
                      slotProps={{ select: { multiple: true } }}
                      value={s.allowed_roles}
                      onChange={(e) =>
                        change(i, "allowed_roles", e.target.value)
                      }
                    >
                      {["user", "manager", "admin"].map((r) => (
                        <MenuItem value={r} key={r}>
                          {r}
                        </MenuItem>
                      ))}
                    </TextField>
                    <Stack direction="row" flexWrap="wrap">
                      <FormControlLabel
                        label="Активен"
                        control={
                          <Checkbox
                            checked={s.active}
                            onChange={(e) =>
                              change(i, "active", e.target.checked)
                            }
                          />
                        }
                      />
                      <FormControlLabel
                        label="Необязательный"
                        control={
                          <Checkbox
                            checked={s.optional}
                            onChange={(e) =>
                              change(i, "optional", e.target.checked)
                            }
                          />
                        }
                      />
                      {[-1, 1].map((offset) => (
                        <Button
                          key={offset}
                          disabled={
                            i + offset < 0 || i + offset >= edit.stages.length
                          }
                          onClick={() => {
                            const stages = [...edit.stages];
                            [stages[i], stages[i + offset]] = [
                              stages[i + offset],
                              stages[i],
                            ];
                            setEdit({ ...edit, stages });
                          }}
                        >
                          {offset === -1 ? "↑ Выше" : "↓ Ниже"}
                        </Button>
                      ))}
                    </Stack>
                  </Stack>
                </Paper>
              ))}
              <Button
                onClick={() =>
                  setEdit({ ...edit, stages: [...edit.stages, fresh()] })
                }
              >
                Добавить этап
              </Button>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button disabled={busy} onClick={() => setEdit(null)}>
              Отмена
            </Button>
            <Button
              variant="contained"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  const payload = {
                    name: edit.name,
                    description: edit.description,
                    active: edit.active,
                    version: edit.version,
                    stages: edit.stages.map((s: Row, i: number) => ({
                      id: s.id,
                      name: s.name,
                      description: s.description,
                      active: s.active,
                      optional: s.optional,
                      allowed_roles: s.allowed_roles,
                      order_index: i,
                    })),
                  };
                  await api.request({
                    url: `/workflows${edit.id ? "/" + edit.id : ""}`,
                    method: edit.id ? "PUT" : "POST",
                    data: payload,
                  });
                  await qc.invalidateQueries();
                  setEdit(null);
                } catch (e) {
                  setError(message(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              Сохранить
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </>
  );
}
