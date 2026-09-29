import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DataTable, Editor, State, ErrorBoundary } from "./common";

describe("Основные компоненты", () => {
  it("отображает пустое состояние", () => {
    render(<DataTable rows={[]} columns={{ name: "Название" }} />);
    expect(
      screen.getByText("По выбранным условиям записей нет"),
    ).toBeInTheDocument();
  });
  it("открывает выбранную строку", () => {
    const click = vi.fn();
    render(
      <DataTable
        rows={[{ id: 1, name: "ИТМО" }]}
        columns={{ name: "Название" }}
        onRow={click}
      />,
    );
    fireEvent.click(screen.getByText("ИТМО"));
    expect(click).toHaveBeenCalledWith({ id: 1, name: "ИТМО" });
  });
  it("показывает понятную ошибку", () => {
    render(
      <State query={{ isPending: false, error: new Error("Нет соединения") }}>
        данные
      </State>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Нет соединения");
  });
  it("сохраняет форму без перезагрузки", async () => {
    const save = vi.fn().mockResolvedValue({}),
      close = vi.fn();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <Editor
          title="Новая программа"
          fields={[{ key: "name", label: "Название", required: true }]}
          initial={{ name: "" }}
          onSave={save}
          onClose={close}
        />
      </QueryClientProvider>,
    );
    fireEvent.change(screen.getByLabelText(/Название/), {
      target: { value: "Python" },
    });
    fireEvent.click(screen.getByText("Сохранить"));
    await waitFor(() => expect(save).toHaveBeenCalledWith({ name: "Python" }));
    await waitFor(() => expect(close).toHaveBeenCalled());
  });
  it("перехватывает ошибку рендера", () => {
    function Broken(): never {
      throw Error("test");
    }
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Ошибка интерфейса");
    spy.mockRestore();
  });
});
