# LASTIVKA_ASSISTANT_CHARTER v1.1
workflow: PLAN → DRY-RUN → APPLY → VERIFY → COMMIT_MSG
rules:
  - No deletes/moves outside temp/ без явного ОК.
  - vendors/, archive/ — -text (не нормалізувати).
  - Snapshot+manifest перед ризиковими кроками.
  - «Хірургічні» правки з коротким дифом у коміті.
  - EOL/BOM керуємо .gitattributes/.editorconfig.
  - Скрипти CWD-агностичні; pre-commit = Clean-Caches (DRY-RUN).
