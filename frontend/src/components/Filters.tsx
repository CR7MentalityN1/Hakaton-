import { Button, MenuItem, Paper, TextField } from "@mui/material";
import { useData, type Row } from "./common";
export function Filters({
  value,
  onChange,
}: {
  value: Row;
  onChange: (v: Row) => void;
}) {
  const universities = useData("/universities", { page_size: 1000 }),
    directions = useData("/directions", { page_size: 1000 }),
    programs = useData("/programs", { page_size: 1000 }),
    products = useData("/products", { page_size: 1000 }),
    users = useData("/users", { page_size: 1000 }),
    workflows = useData("/workflows");
  const lists: [string, string, Row[]][] = [
    ["university_id", "ВУЗ", universities.data?.items ?? []],
    ["direction_id", "Направление", directions.data?.items ?? []],
    ["program_id", "Программа", programs.data?.items ?? []],
    ["product_id", "Продукт", products.data?.items ?? []],
    [
      "responsible_employee_id",
      "Ответственный",
      (users.data?.items ?? []).map((u: Row) => ({ ...u, name: u.full_name })),
    ],
    ["stage_id", "Этап", (workflows.data ?? []).flatMap((w: Row) => w.stages)],
  ];
  return (
    <Paper
      variant="outlined"
      sx={{ p: 2, mb: 3, display: "flex", gap: 2, flexWrap: "wrap" }}
    >
      {["start", "end"].map((key, i) => (
        <TextField
          key={key}
          size="small"
          label={i ? "Период до" : "Период с"}
          type="date"
          slotProps={{ inputLabel: { shrink: true } }}
          value={value[key] ?? ""}
          onChange={(e) =>
            onChange({ ...value, [key]: e.target.value || undefined })
          }
        />
      ))}
      {lists.map(([key, label, items]) => (
        <TextField
          sx={{ minWidth: 160, flex: 1 }}
          select
          size="small"
          key={key}
          label={label}
          value={value[key] ?? ""}
          onChange={(e) =>
            onChange({
              ...value,
              [key]: e.target.value ? Number(e.target.value) : undefined,
            })
          }
        >
          <MenuItem value="">Все</MenuItem>
          {items.map((item) => (
            <MenuItem value={item.id} key={item.id}>
              {item.name}
            </MenuItem>
          ))}
        </TextField>
      ))}
      <Button onClick={() => onChange({})}>Сбросить</Button>
    </Paper>
  );
}
