# BitVision Analytics

Web app to view, filter and analyse the tender outcomes saved in BitVision.
Data can be grouped by any field and shows average, min and max for amount awarded
and downside. Results can be exported to Excel and PDF.

The app connects to the BitVision database in read-only mode.

- backend: Python (FastAPI)
- frontend: React


## Requirements

- Python 3.11 or 3.12
- Node.js 20+
- MySQL 8 with the BitVision database (tender_outcomes table must exist)
- Docker (only for server deploy)


## Run on Mac

Backend:

```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
brew install pango
```

Set the database connection in `backend/.env`:

```
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/bitvision_development
```

Start it:

```
uvicorn app.main:app --reload
```

Frontend (in another terminal):

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173


## Run on Windows

Use PowerShell.

Backend:

```
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set `DATABASE_URL` in `backend\.env` same as above, then:

```
uvicorn app.main:app --reload
```

For PDF export on Windows you need Pango. Install MSYS2 (https://www.msys2.org),
run `pacman -S mingw-w64-ucrt-x86_64-pango` in the MSYS2 UCRT64 terminal and add
`C:\msys64\ucrt64\bin` to PATH. Or just use Docker.

Frontend (in another window):

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173


## Sample data

Only for local testing, don't run it on production.

Mac:

```
cd backend
SEED_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/bitvision_development python scripts/seed_sample_data.py --rows 500
```

Windows:

```
cd backend
$env:SEED_DATABASE_URL="mysql+pymysql://root:password@127.0.0.1:3306/bitvision_development"
python scripts\seed_sample_data.py --rows 500
```


## Tests

```
cd backend
pytest
```


## Deploy with Docker

Same steps on Mac, Windows and Linux.

1. Create a read-only MySQL user on the BitVision database:

```
CREATE USER 'analytics_ro'@'%' IDENTIFIED BY 'password';
GRANT SELECT ON bitvision_production.tender_outcomes TO 'analytics_ro'@'%';
FLUSH PRIVILEGES;
```

2. Create `backend/.env`:

```
DATABASE_URL=mysql+pymysql://analytics_ro:password@DB_HOST:3306/bitvision_production
```

If MySQL runs on the same machine as Docker use `host.docker.internal` as DB_HOST.

3. Start:

```
docker compose up -d --build
```

App runs on http://server-address:8080

To update after a code change:

```
git pull
docker compose up -d --build
```


## API

- `GET /api/outcomes` - filtered data, paginated
- `GET /api/olap` - grouped data with avg, min, max
- `GET /api/export/excel` - Excel export
- `GET /api/export/pdf` - PDF export
- `GET /api/meta` - available group by fields

API docs: http://localhost:8000/docs
