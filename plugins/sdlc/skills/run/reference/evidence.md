# Evidence, findings and reporting

## Evidence row
`AC/question → version (SHA, dirty?) → environment → command or observation → expected → actual → status → link`
Status: **PASS** (ran, matched), **FAIL** (ran, did not match), **NOT RUN** (not executed — say why and who can run it),
**BLOCKED** (cannot run until X), **N/A** (does not apply — say why). A simulator, a mock or one lucky request is not device
evidence; a green build is not acceptance; author self-review is not independent review. Never paste secrets or personal data.

## Findings severity (reviewer)
- **P0** — breaks the product, loses data, leaks secrets, violates a hard rule → must fix before merge.
- **P1** — an AC is not met, a likely bug, a missing test for changed behaviour, a security/privacy weakness → fix before merge.
- **P2** — maintainability, clarity, small edge cases → fix if cheap, otherwise record.
- **P3** — style/nit → optional.
Each finding: location (file:line), what is wrong, evidence, suggested fix.

## Report to the owner (in config.owner_language; the example is Russian)
```
<Change> «<title>» — <готово | ждёт тебя | заблокировано>
Сделано: 3–6 пунктов · PR: #…
Проверки: тесты n ✔ · CI ✔ · ревью ✔ · AC: x/y PASS, z NOT RUN (почему)
Тебе: нумерованные шаги, если нужен ты (или «ничего»); ответ: /sdlc:decide <ID> <ответ>
Дальше: следующий шаг или этап
```
