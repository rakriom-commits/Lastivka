# Self Orchestration (L6)

Етап: Оркестрація Ластівки.

- Політика: `tools/self_orchestration_policy.json`
- Історія: `tools/outbox/self_orchestration_history.json`
- Призначення: синхронізація та координація модулів.

Можливості:
- Sync  узгодження станів між модулями
- Propagate  поширення стабільних змін
- Report  створення узагальнених звітів

Критичні області (`memory`, `kernel`, `security`) змінюються лише вручну.
