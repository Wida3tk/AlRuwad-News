# AlRuwad News

Arabic news platform MVP for importing, editing, and publishing translated news articles.

## Local Run

```bash
python server.py
```

Open:

```text
http://127.0.0.1:4174
```

Default local admin:

```text
admin / alruwad2026
```

For deployment, set these environment variables:

```text
ALRUWAD_ADMIN_USER
ALRUWAD_ADMIN_PASSWORD
PORT
```

## Notes

- The local SQLite database is stored in `data/alruwad.db`.
- `data/` is intentionally ignored by Git so local drafts and test data are not uploaded.
- On first run, the app creates a fresh database and seed articles automatically.
