import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
export function useData<T = any>(path: string, params?: unknown) {
  return useQuery<T>({
    queryKey: [path, params],
    queryFn: async () => (await api.get(path, { params })).data,
  });
}
