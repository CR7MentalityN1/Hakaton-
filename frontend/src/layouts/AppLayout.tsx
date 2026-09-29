import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  Toolbar,
  Typography,
  Snackbar,
  Alert,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { useAuth } from "../auth/Auth";
const links = [
  ["/", "Dashboard"],
  ["/universities", "ВУЗы"],
  ["/interactions", "Взаимодействия"],
  ["/directions", "ИТ-направления"],
  ["/programs", "ИТ-программы"],
  ["/products", "ИТ-продукты"],
  ["/workflows", "Workflow"],
  ["/reports", "Отчёты"],
  ["/import", "Импорт"],
  ["/integrations", "Интеграции"],
  ["/users", "Пользователи"],
  ["/audit", "Журнал аудита"],
  ["/settings", "Настройки"],
  ["/help", "Руководство"],
];
export default function AppLayout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [notification, setNotification] = useState("");
  useEffect(() => {
    const listener = (event: Event) =>
      setNotification((event as CustomEvent<string>).detail);
    window.addEventListener("crm:notification", listener);
    return () => window.removeEventListener("crm:notification", listener);
  }, []);
  const location = useLocation();
  const nav = (
    <>
      <Box sx={{ p: 3 }}>
        <Typography fontWeight={800} fontSize={24}>
          РТК<span style={{ color: "#ff8650" }}> / </span>ИТ Школа
        </Typography>
        <Typography variant="caption" sx={{ opacity: 0.7 }}>
          ПАРТНЁРСКАЯ ПЛАТФОРМА
        </Typography>
      </Box>
      <List sx={{ px: 2 }}>
        {links
          .filter(
            ([p]) =>
              !(
                ["/audit", "/settings", "/users"].includes(p) &&
                user.role !== "admin"
              ) && !(p === "/import" && user.role === "user"),
          )
          .map(([path, name]) => (
            <ListItemButton
              key={path}
              component={Link}
              to={path}
              selected={
                path === "/"
                  ? location.pathname === "/"
                  : location.pathname.startsWith(path)
              }
              onClick={() => setOpen(false)}
              sx={{
                borderRadius: 2,
                mb: 0.3,
                "&.Mui-selected": { bgcolor: "#ffffff20" },
                "&.Mui-selected:hover": { bgcolor: "#ffffff30" },
              }}
            >
              <ListItemText primary={name} />
            </ListItemButton>
          ))}
      </List>
      <Typography variant="caption" sx={{ px: 3, py: 2, opacity: 0.65 }}>
        Демонстрационная среда · v2.0
      </Typography>
    </>
  );
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Snackbar
        open={!!notification}
        autoHideDuration={4000}
        onClose={() => setNotification("")}
      >
        <Alert severity="success" onClose={() => setNotification("")}>
          {notification}
        </Alert>
      </Snackbar>
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", md: "block" },
          width: 260,
          "& .MuiDrawer-paper": {
            width: 260,
            bgcolor: "#24163a",
            color: "white",
            border: 0,
          },
        }}
      >
        {nav}
      </Drawer>
      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        sx={{
          "& .MuiDrawer-paper": {
            width: 260,
            bgcolor: "#24163a",
            color: "white",
          },
        }}
      >
        {nav}
      </Drawer>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <AppBar
          position="sticky"
          color="inherit"
          elevation={0}
          sx={{ borderBottom: "1px solid #e8e5ee" }}
        >
          <Toolbar>
            <IconButton
              sx={{ display: { md: "none" }, mr: 1 }}
              onClick={() => setOpen(true)}
              aria-label="Открыть меню"
            >
              <MenuIcon />
            </IconButton>
            <Typography sx={{ flex: 1 }} color="text.secondary">
              Управление образовательными программами
            </Typography>
            <Stack direction="row" alignItems="center" gap={1}>
              <Avatar sx={{ width: 32, height: 32, bgcolor: "primary.main" }}>
                {user.full_name[0]}
              </Avatar>
              <Typography sx={{ display: { xs: "none", sm: "block" } }}>
                {user.full_name}
              </Typography>
              <Chip size="small" label={user.role} />
              <Button onClick={logout}>Выйти</Button>
            </Stack>
          </Toolbar>
        </AppBar>
        <Box
          component="main"
          sx={{ p: { xs: 2, md: 4 }, maxWidth: 1800, mx: "auto" }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
