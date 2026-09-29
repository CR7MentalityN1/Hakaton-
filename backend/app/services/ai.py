from datetime import timezone
from typing import Protocol
from app.models import utcnow


class AIWorkflowAssistant(Protocol):
    def suggest(self, interaction) -> list[str]: ...


class RuleBasedAssistant:
    def suggest(self, item):
        hints = []
        if not item.license_signed:
            hints.append(
                "Отсутствует подписанная лицензия. Рекомендуется проверить статус документов."
            )
        if not item.contract_number:
            hints.append("Заполните номер договора до передачи материалов.")
        if not item.responsible_employee_id:
            hints.append("Назначьте ответственного сотрудника за взаимодействие.")
        updated = (
            item.updated_at.replace(tzinfo=timezone.utc)
            if item.updated_at.tzinfo is None
            else item.updated_at
        )
        if (utcnow() - updated).days >= 14:
            hints.append(
                "Более 14 дней без изменений. Свяжитесь с представителем вуза."
            )
        if not hints:
            hints.append(
                "Данные заполнены. Проверьте готовность к следующему активному этапу workflow."
            )
        return hints


assistant: AIWorkflowAssistant = RuleBasedAssistant()
