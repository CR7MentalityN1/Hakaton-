export function notifySuccess(message = "Изменения сохранены") {
  window.dispatchEvent(
    new CustomEvent("crm:notification", { detail: message }),
  );
}
