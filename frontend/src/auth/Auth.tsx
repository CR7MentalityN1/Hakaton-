import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import Keycloak from "keycloak-js";
import {
  Alert,
  Button,
  Container,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";
import { api, message } from "../api/client";
export type Employee = {
  id: number;
  full_name: string;
  email: string;
  role: "user" | "manager" | "admin";
  keycloak_user_id: string;
  active: boolean;
  manager_id: number | null;
};
export const AuthContext = createContext<{
  user: Employee;
  logout: () => void;
} | null>(null);
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw Error("Нет контекста авторизации");
  return value;
}
let session: Promise<Keycloak> | undefined;
function connect() {
  return (session ??= (async () => {
    const { data } = await api.get("/auth/config");
    const kc = new Keycloak({
      url: data.url,
      realm: data.realm,
      clientId: data.clientId,
    });
    await kc.init({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
    });
    api.interceptors.request.use(async (config) => {
      await kc.updateToken(30);
      config.headers.Authorization = `Bearer ${kc.token}`;
      return config;
    });
    return kc;
  })());
}
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Employee>();
  const [error, setError] = useState("");
  const [kc, setKC] = useState<Keycloak>();
  useEffect(() => {
    let live = true;
    connect()
      .then(async (client) => {
        const { data } = await api.get<Employee>("/auth/me");
        if (live) {
          setUser(data);
          setKC(client);
        }
      })
      .catch((e) => {
        if (live) setError(message(e));
      });
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    if (!user) return;
    const timer = setInterval(() => {
      api
        .get<Employee>("/auth/me")
        .then(({ data }) => setUser(data))
        .catch((e) => setError(message(e)));
    }, 30000);
    return () => clearInterval(timer);
  }, [!!user]);
  if (error)
    return (
      <Container sx={{ py: 10 }}>
        <Stack spacing={3}>
          <Typography variant="h4">Не удалось войти в CRM</Typography>
          <Alert severity="error">{error}</Alert>
          <Button onClick={() => location.reload()}>Повторить вход</Button>
        </Stack>
      </Container>
    );
  if (!user || !kc)
    return (
      <Container sx={{ py: 10 }}>
        <Typography variant="h5" mb={3}>
          ИТ Школа · Подключение к Keycloak
        </Typography>
        <LinearProgress />
      </Container>
    );
  return (
    <AuthContext.Provider
      value={{
        user,
        logout: () => void kc.logout({ redirectUri: location.origin }),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
