import axios from "axios";
export const api = axios.create({ baseURL: "/api/v1", timeout: 120000 });
export function message(error: unknown): string {
  return axios.isAxiosError(error)
    ? error.response?.data?.message || error.message
    : error instanceof Error
      ? error.message
      : "Не удалось выполнить операцию";
}
export async function download(
  path: string,
  filename: string,
  body?: unknown,
  params?: unknown,
) {
  const response = await api.request({
    url: path,
    method: body ? "POST" : "GET",
    data: body,
    params,
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
