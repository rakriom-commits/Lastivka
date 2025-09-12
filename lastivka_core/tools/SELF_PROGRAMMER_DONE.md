# Self Programmer (L3)

Цей модуль дозволяє Ластівці пропонувати та застосовувати патчі:
- Пропозиції  `tools/outbox/patches/`
- Історія  `tools/outbox/self_programmer_history.json`
- Політика  `tools/self_programmer_policy.json`
- Повний цикл включає dry-run, apply, тести, коміт.

Критичні області (`memory`, `kernel`, `security`) змінюються лише вручну.
