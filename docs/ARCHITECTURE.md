# Архитектура плагина `sdlc`

## 1. Состав
```text
claude-code-sdlc/                     репозиторий = маркетплейс Claude Code
├── .claude-plugin/marketplace.json   каталог из одного плагина "sdlc"
├── plugins/sdlc/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   ├── run/          /sdlc:run — оркестратор
│   │   │   ├── SKILL.md      протокол цикла, границы, качество
│   │   │   ├── phases/       10 процедур фаз (читаются по одной)
│   │   │   ├── reference/    risk.md, autonomy.md, evidence.md
│   │   │   └── templates/    intent, spec, plan, feature, handoff, report, review, release, incident, adr
│   │   ├── status/       /sdlc:status — где мы (ничего не меняет)
│   │   ├── decide/       /sdlc:decide — решение владельца (только пользователь)
│   │   ├── init/         /sdlc:init — подготовка .sdlc/ в проекте
│   │   └── incident/     /sdlc:incident — ветка инцидента
│   ├── agents/           reviewer.md, verifier.md (без Edit/Write)
│   ├── hooks/hooks.json  SessionStart, UserPromptSubmit, PreToolUse×2, Stop
│   ├── scripts/          sdlc.py (состояние), hooklib.py, guard_bash.py, guard_write.py,
│   │                     stop_continue.py, session_context.py, owner_prompt.py
│   └── profiles/         generic/, lingo/ — config.json, PROJECT.md, state.json
├── docs/                 GUIDE, AUDIT, ARCHITECTURE, LINGO
├── tests/test_plugin.py  31 тест (unittest, stdlib)
└── start.sh              запуск из терминала (установка/обновление плагина + /sdlc:run)
```

## 2. Данные в проекте
`.sdlc/` в корне проекта коммитится в Git, кроме `runtime/`:
- `config.json`: языки, команды проверок, `merge_policy`, защищённые ветки и пути, запреты проекта, ночное окно, жёсткие правила;
- `PROJECT.md`: профиль проекта (≤ 1 страницы): источники истины, решения владельца в силе, ворота;
- `state.json`: изменение, этап продукта, фаза, статус (`in_progress | waiting_owner | blocked | done`), риск, режим
  (`auto | step`), ворота, очередь, `next`, история (последние 40 событий), сведения об автозапуске;
- `survey.md`: результат обследования;
- `runtime/stop.json`: счётчики Stop-хука, не коммитится.

Артефакты изменения — `docs/changes/<ID>/` (`changes_dir`). `sdlc.py advance` не выпускает из фазы без её выходного артефакта:
survey → `.sdlc/survey.md`, intent → intent|feature, spec → spec|feature, plan → plan|feature, build → handoff, verify → report,
review → review|report, release → release (если выпуск включён), incident → incident.

## 3. Хуки
Все хуки ничего не делают вне проектов с `.sdlc/`. Ошибка в самом хуке пропускает действие, а не ломает сессию.
Совпадение с правилом блокирует действие.

| Событие | Скрипт | Поведение |
|---|---|---|
| SessionStart (startup/resume/clear/compact) | session_context.py | добавляет в контекст статус SDLC; после compact напоминает перечитать state и handoff |
| UserPromptSubmit | owner_prompt.py | если владелец набрал `/sdlc:decide …`, записывает решение (`decided_by: owner`); повтор безопасен |
| PreToolUse Bash | guard_bash.py | блокирует force-push, push в защищённые ветки (и с них без refspec), удаление и зеркалирование веток, `reset --hard`, `clean -f`, переписывание истории, сброс рабочей копии, `gh pr merge` при `merge_policy=owner` и всегда `--admin`, `gh repo delete/…`, `gh secret/auth`, `rm -rf` по корню и дому, `decide-raw` от модели, запись `state.json` в обход скрипта, доступ к `protected_paths`, `deny_commands` проекта, `night_only_commands` вне ночного окна |
| PreToolUse Write/Edit/MultiEdit/NotebookEdit | guard_write.py | блокирует секреты в содержимом (Groq, Anthropic, OpenRouter, OpenAI, AWS, Google, GitHub, Slack, приватные ключи), запись в защищённые пути и прямое редактирование `state.json` |
| Stop | stop_continue.py | при активном автозапуске (`run.active`, `mode=auto`, та же сессия, статус `in_progress`) возвращает `decision: block` с подсказкой следующего шага; отпускает после 2 продолжений без прогресса (по хешу state + HEAD + git status) или по исчерпании `max_auto_continuations` |

Почему решение владельца нельзя подделать: модель не вызывает хук UserPromptSubmit. Навык `decide` помечен
`disable-model-invocation`, а `sdlc.py gate decide --by owner` всегда отказывает. Вызов `decide-raw` моделью блокирует Bash-guard,
прямую правку `state.json` — оба guard. Ограничение: guard проверяет текст команды и не является песочницей.

## 4. Протокол `/sdlc:run`
1. Подставить текущий статус (`!` sdlc.py status). Если `.sdlc/` нет — `init` с автоопределением профиля (Lingo — по remote
   `itmax04/lingo`).
2. `activate --session ${CLAUDE_SESSION_ID} --mode auto|step`.
3. Цикл: процедура фазы → артефакты → `handoff.md` → `set --next` → `advance`. Ворота ставят статус `waiting_owner`, после чего
   агент делает независимую работу и останавливается с отчётом.
4. Ревью и проверка — агентами `sdlc:reviewer` и `sdlc:verifier`. Merge — только по политике и условиям.
5. Завершение: статус → отчёт владельцу (5 строк) → Stop-хук отпускает сессию.

## 5. Расширение
- Новый проект: `/sdlc:init` (generic) и заполнить `config.json`/`PROJECT.md`, или добавить профиль в `profiles/<name>/`.
- Новое правило: сначала тест в `tests/test_plugin.py`, затем правка хука, затем `python3 -m unittest`
  и `claude plugin validate plugins/sdlc --strict`.
- Версия: поднять `version` в `plugin.json` и запушить; пользователи обновляют командой `claude plugin update sdlc@claude-code-sdlc`
  или через `start.sh`, который делает это сам.
