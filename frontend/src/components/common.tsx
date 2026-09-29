import { useState, type ReactNode, Component } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Checkbox,
  FormControlLabel,
} from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { message } from "../api/client";
import type { Row, Field } from "../types";
import { notifySuccess } from "../utils/notifications";
export type { Row, Field } from "../types";
export { useData } from "../hooks/useData";
export function State({
  query,
  children,
}: {
  query: { isPending: boolean; error: unknown };
  children: ReactNode;
}) {
  if (query.isPending)
    return (
      <Stack gap={2}>
        <Skeleton height={100} />
        <Skeleton height={300} />
      </Stack>
    );
  if (query.error)
    return <Alert severity="error">{message(query.error)}</Alert>;
  return <>{children}</>;
}
export function Title({
  children,
  action,
}: {
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Stack
      direction="row"
      justifyContent="space-between"
      alignItems="center"
      mb={3}
      gap={2}
    >
      <Typography variant="h4" fontWeight={750}>
        {children}
      </Typography>
      {action}
    </Stack>
  );
}
export function DataTable({
  rows,
  columns,
  onRow,
}: {
  rows: Row[];
  columns: Record<string, string>;
  onRow?: (r: Row) => void;
}) {
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            {Object.values(columns).map((v) => (
              <TableCell key={v}>{v}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length ? (
            rows.map((row, i) => (
              <TableRow
                key={row.id ?? i}
                hover
                onClick={() => onRow?.(row)}
                sx={{ cursor: onRow ? "pointer" : "default" }}
              >
                {Object.keys(columns).map((k) => (
                  <TableCell key={k}>
                    {typeof row[k] === "object"
                      ? JSON.stringify(row[k])
                      : typeof row[k] === "boolean"
                        ? row[k]
                          ? "Да"
                          : "Нет"
                        : String(row[k] ?? "—")}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={Object.keys(columns).length}>
                <Box py={4} textAlign="center">
                  По выбранным условиям записей нет
                </Box>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
export function Editor({
  title,
  fields,
  initial,
  onSave,
  onClose,
}: {
  title: string;
  fields: Field[];
  initial: Row;
  onSave: (v: Row) => Promise<unknown>;
  onClose: () => void;
}) {
  const [value, setValue] = useState(initial);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const qc = useQueryClient();
  return (
    <Dialog open onClose={() => !busy && onClose()} fullWidth maxWidth="md">
      <Box
        component="form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await onSave(value);
            await qc.invalidateQueries();
            notifySuccess();
            onClose();
          } catch (e) {
            setError(message(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <Stack gap={2} pt={1}>
            {error && <Alert severity="error">{error}</Alert>}
            {fields.map((f) =>
              f.type === "boolean" ? (
                <FormControlLabel
                  key={f.key}
                  label={f.label}
                  control={
                    <Checkbox
                      checked={!!value[f.key]}
                      onChange={(e) =>
                        setValue({ ...value, [f.key]: e.target.checked })
                      }
                    />
                  }
                />
              ) : (
                <TextField
                  key={f.key}
                  label={f.label}
                  required={f.required}
                  disabled={f.disabled || busy}
                  type={
                    f.type === "number"
                      ? "number"
                      : f.type === "date"
                        ? "date"
                        : "text"
                  }
                  slotProps={{ inputLabel: { shrink: true } }}
                  select={!!f.options}
                  multiline={f.type === "textarea"}
                  minRows={f.type === "textarea" ? 3 : undefined}
                  value={value[f.key] ?? ""}
                  onChange={(e) =>
                    setValue({
                      ...value,
                      [f.key]:
                        f.type === "number" ||
                        (f.options && typeof f.options[0]?.id === "number")
                          ? e.target.value === ""
                            ? null
                            : Number(e.target.value)
                          : f.type === "date"
                            ? e.target.value || null
                            : e.target.value,
                    })
                  }
                >
                  {f.options && [
                    <MenuItem key="empty" value="">
                      Не выбрано
                    </MenuItem>,
                    ...f.options.map((o) => (
                      <MenuItem key={o.id} value={o.id}>
                        {o.name}
                      </MenuItem>
                    )),
                  ]}
                </TextField>
              ),
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button disabled={busy} onClick={onClose}>
            Отмена
          </Button>
          <Button disabled={busy} type="submit" variant="contained">
            {busy ? "Сохранение…" : "Сохранить"}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <Alert severity="error">
        Ошибка интерфейса.{" "}
        <Button onClick={() => location.reload()}>Перезагрузить</Button>
      </Alert>
    ) : (
      this.props.children
    );
  }
}
