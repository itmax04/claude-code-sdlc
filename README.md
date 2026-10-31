# Claude Code SDLC

Плагин Claude Code, который ведёт разработку по AI-native SDLC одной командой: **`/sdlc:run`**.

Цепочка фаз: survey → intent → spec → plan → build ↔ verify → review → release → maintain, плюс incident.
- Состояние хранится в репозитории (`.sdlc/`), поэтому любая новая сессия продолжает с того же места.
- Работа идёт без остановок до ворот, где действительно нужен владелец: ключи, деньги, устройства, production, приёмка.
- Ревью и проверку выполняют независимые агенты.
- Хуки технически запрещают опасные действия: force-push, push в main, секреты в файлах, дорогие прогоны днём и другие.

Сделано на основе прежнего SDLC владельца (руководство AI-native SDLC и пакет фаз Lingo для Codex) и полностью переработано под
возможности Claude Code. Что изменено и почему — [docs/AUDIT.md](docs/AUDIT.md).

## Быстрый старт

**В приложении Claude (вкладка Code)** — откройте папку проекта, например `~/Developer/lingo`, и наберите:
```
/plugin install sdlc --marketplace itmax04/claude-code-sdlc
```
Установка нужна один раз; в открывшейся панели выберите область «user». Затем:
```
/sdlc:run
```

**Из терминала** — одна команда: клонирует репозиторий при необходимости, ставит или обновляет плагин и запускает SDLC:
```bash
[ -d ~/Developer/claude-code-sdlc ] || gh repo clone itmax04/claude-code-sdlc ~/Developer/claude-code-sdlc; ~/Developer/claude-code-sdlc/start.sh ~/Developer/lingo
```

## Команды в Claude Code
| Команда | Что делает |
|---|---|
| `/sdlc:run` | запустить или продолжить SDLC текущего проекта; при первом запуске сама создаёт `.sdlc/` |
| `/sdlc:run step` | выполнить только текущую фазу и остановиться с отчётом |
| `/sdlc:run new <идея>` | начать новое изменение с брейншторма |
| `/sdlc:status` | где мы, что ждёт владельца, что дальше (ничего не меняет) |
| `/sdlc:decide <ID> <ответ>` | записать решение владельца по воротам, например `/sdlc:decide G-CHAIN принимаю` |
| `/sdlc:init [profile]` | подготовить `.sdlc/` в новом проекте (`generic` или `lingo`) |
| `/sdlc:incident <что случилось>` | ветка инцидента из любой фазы |

## Документация
- [docs/GUIDE.md](docs/GUIDE.md) — методология: фазы, риск R0–R4, границы автономии, доказательства, DoD
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — устройство: навыки, агенты, хуки, состояние, защита
- [docs/AUDIT.md](docs/AUDIT.md) — аудит прежнего SDLC и список улучшений
- [docs/LINGO.md](docs/LINGO.md) — переход проекта Lingo с Codex-пакетов

## Проверка самого плагина
```bash
python3 -m unittest discover -s tests -v
```
```bash
claude plugin validate plugins/sdlc --strict
```

## Требования
Claude Code 2.1.292 или новее (проверено на 2.1.309), `git`, `python3` 3.9 или новее (есть в macOS), для GitHub-шагов — `gh`.
Лицензия MIT.
