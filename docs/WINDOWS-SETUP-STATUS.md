# Состояние подготовки Windows

**Актуальное решение пользователя: Docker и WSL2 локально не устанавливать. Дальнейшие системные операции из исторической инструкции ниже не выполнять.** Разработка и проверки продолжаются без Docker; для запуска подготовленного стенда используется `start-local.bat`. Контейнерная конфигурация сохранена для проверки на другом хосте.

28 сентября 2026: пользователь разрешил установку Docker/WSL2 и необходимые системные изменения. Перезагрузка автоматически не выполнялась.

## Выполнено

- Установлен WSL 2.7.14 (ядро 6.18.33.2).
- Скачан официальный Docker Desktop 4.93.0.240920 в `.runtime/Docker Desktop Installer.exe`; цифровая подпись Docker Inc проверена и действительна.
- Установщик Docker распаковал файлы в `C:\Program Files\Docker\Docker`, затем перешёл к включению компонентов Windows. Установка пока НЕ подтверждена как завершённая.
- `docker compose config --quiet` проходит через автономный Compose CLI.
- Дополнен `scripts/verify-compose.ps1`: проверка PostgreSQL/Redis, миграции, OIDC discovery/JWKS и frontend API proxy.

## Системная блокировка

Первоначальный `wsl --install --no-distribution` завершил установку WSL, но включение VirtualMachinePlatform вернуло ошибку 14098 (повреждено хранилище компонентов Windows).

Повторная попытка включения VirtualMachinePlatform и Microsoft-Windows-Subsystem-Linux из установщика Docker ожидает Windows Update. В CBS и журнале Windows Update зафиксирован код `0x80242005`. Штатный перезапуск службы wuauserv ожидает её остановки. Восстановление DISM поставлено в ожидание завершения текущей операции; успешный RestoreHealth не заявляется.

Журналы:

- `C:\Windows\Logs\CBS\CBS.log`
- `C:\Windows\Logs\DISM\dism.log`
- `C:\ProgramData\DockerDesktop\install-log-admin.txt`

## После сохранения работы и перезагрузки

### Проверка после выполненной пользователем перезагрузки

28.09.2026, 18:22–18:36: оба optional feature всё ещё Disabled. Запущен `DISM /Online /Cleanup-Image /RestoreHealth /NoRestart`. Проверка дошла до 100%, но процесс ещё обрабатывает найденные повреждения; итоговый exit code пока не получен. В CBS записаны `0x800f0950 / CBS_E_NO_OPTIONAL_CONTENT_FOUND_FOR_BUILD` и многочисленные `Repair failed: Missing replacement payload`. Не считать восстановление успешным по одному индикатору 100%.

У пользователя запрошен путь к исходному ISO. Проверенные локальные каталоги не содержат установочного образа; подключённого установочного DVD нет. Страница официальных Insider ISO требует входа в учётную запись Windows Insider. Системные файлы вручную не заменялись, повторная перезагрузка не выполнялась.

После перезагрузки повторно запущен native-стенд: PostgreSQL, Keycloak 26.2.5, backend на 8000, frontend на 3000. Браузерный smoke всех трёх ролей прошёл; комментарии, переход workflow, attachment, XLSX download и Excel preview работают. Redis health=degraded — весь Compose не запущен. Результаты в browser-results.json и ACCEPTANCE.md.

Сначала дождаться завершения текущего DISM и проверить последние строки DISM/CBS. Не запускать параллельные операции обслуживания Windows. При наличии совместимого ISO проверить редакцию, архитектуру, язык и версию WIM/ESD, затем использовать его как источник `/Source`; не начинать переустановку Windows.

В PowerShell администратора проверить состояние и восстановить компоненты:

```powershell
DISM.exe /Online /Cleanup-Image /RestoreHealth /NoRestart
sfc.exe /scannow
Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
```

Продолжать включение компонентов только после успешного восстановления. Если RestoreHealth требует источник, нужен официальный совместимый образ Windows: не подменять системные пакеты случайными файлами. Текущая версия ОС: 10.0.28000.1719.

```powershell
DISM.exe /Online /Enable-Feature /FeatureName:VirtualMachinePlatform /FeatureName:Microsoft-Windows-Subsystem-Linux /All /NoRestart
```

Если система потребует ещё одну перезагрузку, предварительно сообщить пользователю. Затем завершить установку Docker из уже скачанного подписанного установщика, запустить Docker Desktop и дождаться `docker info`. Не удалять существующие volumes или native PostgreSQL data.

Перед Compose проверить занятость портов 3000/8000/8080: на них ранее работали процессы этого проекта без Docker. Остановить только подтверждённые процессы проекта.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify-compose.ps1
node scripts/browser-smoke.mjs
node scripts/ui-actions.mjs
python scripts/load_test.py --users 50 --rounds 5
```

После фактического запуска обновить ACCEPTANCE.md и CHECKLIST.md. Docker build, настоящий Redis и совместная работа всех пяти контейнеров пока НЕ проверены.

Официальная инструкция восстановления: https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/repair-a-windows-image
