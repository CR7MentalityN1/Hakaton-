import { useState } from "react";
import { Box, Button, Paper, Stack, Typography, Alert } from "@mui/material";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
} from "recharts";
import { Filters } from "../components/Filters";
import {
  State,
  Title,
  useData,
  DataTable,
  type Row,
} from "../components/common";
import { download, message } from "../api/client";
export default function Dashboard() {
  const [filters, setFilters] = useState<Row>({});
  const query = useData("/dashboard", filters);
  const [error, setError] = useState("");
  const d = query.data;
  return (
    <>
      <Title>Обзор сотрудничества</Title>
      <Typography color="text.secondary" mb={3}>
        Образовательные программы, партнёры и результаты ИТ Школы
      </Typography>
      <Filters value={filters} onChange={setFilters} />
      <State query={query}>
        {d && (
          <>
            <Box className="cards">
              {Object.entries({
                universities: "ВУЗы",
                interactions: "Взаимодействия",
                programs: "ИТ-программы",
                products: "ИТ-продукты",
                applications: "Заявки",
                students: "Обучающиеся",
                streams: "Потоки",
              }).map(([key, label]) => (
                <Paper key={key} variant="outlined" sx={{ p: 2.5 }}>
                  <Typography color="text.secondary">{label}</Typography>
                  <Typography variant="h3" mt={1} fontWeight={750}>
                    {d[key]}
                  </Typography>
                </Paper>
              ))}
            </Box>
            <Box className="charts">
              {[
                ["by_status", "ВУЗы по этапам", "universities"],
                ["by_direction", "Взаимодействия по направлениям", "value"],
                ["by_product", "Взаимодействия по продуктам", "value"],
                ["dynamics", "Динамика взаимодействий", "value"],
                ["by_manager", "Нагрузка сотрудников", "value"],
              ].map(([key, title, metric]) => (
                <Paper variant="outlined" sx={{ p: 2, minWidth: 0 }} key={key}>
                  <Typography variant="h6" mb={2}>
                    {title}
                  </Typography>
                  {d[key].length ? (
                    <ResponsiveContainer width="100%" height={280}>
                      {key === "dynamics" ? (
                        <LineChart data={d[key]}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis allowDecimals={false} />
                          <Tooltip />
                          <Line
                            isAnimationActive={false}
                            dataKey={metric}
                            name="Взаимодействия"
                            stroke="#6534b5"
                            strokeWidth={3}
                          />
                        </LineChart>
                      ) : (
                        <BarChart data={d[key]}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                          />
                          <XAxis
                            dataKey="name"
                            tickFormatter={(v) => String(v).slice(0, 14) + "…"}
                            fontSize={10}
                          />
                          <YAxis allowDecimals={false} />
                          <Tooltip />
                          <Bar
                            isAnimationActive={false}
                            dataKey={metric}
                            name={
                              metric === "universities"
                                ? "ВУЗы"
                                : "Взаимодействия"
                            }
                            fill="#6534b5"
                            radius={[5, 5, 0, 0]}
                          />
                        </BarChart>
                      )}
                    </ResponsiveContainer>
                  ) : (
                    <Alert severity="info">Нет данных за период</Alert>
                  )}
                </Paper>
              ))}
            </Box>
            <Paper variant="outlined" sx={{ p: 2, mt: 3 }}>
              <Typography variant="h6" mb={2}>
                Востребованность программ
              </Typography>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={d.ranking}>
                  <XAxis
                    dataKey="name"
                    tickFormatter={(v) => String(v).slice(0, 12) + "…"}
                    fontSize={10}
                  />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar
                    isAnimationActive={false}
                    dataKey="applications"
                    name="Заявки"
                    fill="#6534b5"
                  />
                  <Bar
                    isAnimationActive={false}
                    dataKey="students"
                    name="Обучающиеся"
                    fill="#ff7543"
                  />
                </BarChart>
              </ResponsiveContainer>
              <DataTable
                rows={d.ranking}
                columns={{
                  name: "Программа",
                  applications: "Заявки",
                  students: "Обучающиеся",
                  streams: "Потоки",
                }}
              />
              <Stack direction="row" gap={2} mt={2}>
                {["png", "pdf"].map((f) => (
                  <Button
                    key={f}
                    onClick={() =>
                      download(
                        `/dashboard/chart/${f}`,
                        `chart.${f}`,
                        undefined,
                        filters,
                      ).catch((e) => setError(message(e)))
                    }
                  >
                    Диаграмма {f.toUpperCase()}
                  </Button>
                ))}
              </Stack>
              {error && <Alert severity="error">{error}</Alert>}
            </Paper>
            <Typography variant="h6" mt={3} mb={2}>
              Взаимодействия по этапам
            </Typography>
            <DataTable
              rows={d.by_status}
              columns={{
                name: "Этап",
                value: "Взаимодействия",
                universities: "ВУЗы",
              }}
            />
          </>
        )}
      </State>
    </>
  );
}
