# Lingo: переход с Codex-пакетов на плагин

## Что происходит при первом `/sdlc:run` в `~/Developer/lingo`
1. Плагин видит remote `itmax04/lingo` и создаёт `.sdlc/` из профиля `lingo`. В профиле уже есть решения владельца
   (H-U, H-0, DG-03, D04-01, D01-01), жёсткие правила, команды проверок, запреты и ночное окно Europe/Berlin для evals.
2. Текущее изменение — **P-00 «Принять план улучшений»**, фаза survey. Агент:
   - сверяет живой репозиторий, worktree и PR #1, #31, #34, #33;
   - переносит 15 проверенных документов из архива `…/04-build-P-00-adoption-2026-10-29/outputs/adoption-cycle` в ветку
     поверх `docs/upgrade-plan`, а не продолжает работу в папках;
   - пишет короткие `docs/changes/P-00/` intent, spec и plan из уже принятых материалов, без нового интервью по принятому;
   - обновляет `docs/process/SDLC.md` §4 и `AGENTS.md` §5 под текущие решения (merge после ворот, AI-ревью, `/sdlc:run`);
   - открывает PR, проводит независимое ревью и проверку.
3. Единственный вопрос владельцу на этом этапе — ворота **G-CHAIN**: слить цепочку #1 → #31 → #34 (и затем собственный docs PR).
   Рекомендация: «принимаю», слить по порядку после зелёного CI и AI-ревью. Ответ: `/sdlc:decide G-CHAIN принимаю`.
4. Дальше по очереди: LINGO-07 (редизайн, PR #33, ворота H-07a/H-07b) → LINGO-03 Stage 0 (P-01…P-06, H-1) → Stage 1 → Stage 2 →
   LINGO-04 → LINGO-05 → LINGO-06. Каждый этап начинается с короткого брейншторма по существенным вопросам.

## Соответствие старых фаз
00-preparation → survey · 01-brainstorm-intent → intent · 02-design-spec → spec · 03-plan → plan · 04-build → build ·
05-verification → verify · 06-review → review · 07-deploy → release · 08-maintain → maintain · 09-incident → incident.

## Что больше не нужно
Папки фаз и их ZIP, `00-START-HERE.md` в каждом чате, `tools/packet.py`, `MANIFEST.json`, `PHASE-RESULT.json`, перенос
handoff между чатами. Архив `~/Desktop/Lingo-SDLC-Complete-2026-10-29` (2,1 ГБ) можно сохранить как историю. Агент читает
оттуда только указанное в `.sdlc/state.json → legacy`. Удалять или перемещать архив решает владелец.

## Где смотреть состояние
`/sdlc:status` в Claude Code или файл `.sdlc/state.json`. Живой журнал изменения — `docs/changes/<ID>/handoff.md`.
