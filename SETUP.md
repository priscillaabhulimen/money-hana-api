# SETUP PROJECT

### 1. Install Python
- [ ] Go to the [Python Downloads](https://www.python.org/downloads/) page
- [ ] Download and install Python 3.12 or higher
- [ ] Test by running:

      python3 --version
- [ ] Install the **Python** VSCode Extension by **Microsoft**
- [ ] Install the **Pylance** VSCode Extension by **Microsoft**

### 2. Set up virtual environment
- [ ] In your project directory, run:

      python3 -m venv venv
- [ ] Open View > Command Palette > Python: Select Interpreter
- [ ] Select the virtual environment you just created, or enter the path manually:

      ./venv/bin/python
- [ ] Activate the virtual environment in your terminal:

      source venv/bin/activate
- [ ] Confirm it's active — your terminal prompt should show `(venv)`
- [ ] Add `venv/` to your `.gitignore` if not already there

### 3. Install dependencies
- [ ] Confirm your terminal is running inside the virtual environment
- [ ] Run:

      pip install fastapi[standard] uvicorn[standard] "sqlalchemy[asyncio]" asyncpg pydantic python-dotenv alembic
- [ ] Save your dependencies to requirements.txt:

      pip freeze > requirements.txt
- [ ] Verify installed packages:

      pip freeze

### 4. Configure environment variables
- [ ] Create a `.env` file in the project root
- [ ] Add the following variables:

      DATABASE_URL=postgresql+asyncpg://username:%40password@127.0.0.1:5432/moneyhana_dev
      DEBUG_SQL=true
- [ ] Note: if your password contains special characters, URL-encode them (e.g. `@` → `%40`)
- [ ] Confirm `.env` is in your `.gitignore`
- [ ] Commit `.env.example` to GitHub with placeholder values:

      DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/moneyhana_dev
      DEBUG_SQL=false

### 5. Verify FastAPI is working
- [ ] Start the dev server:

      uvicorn app.main:app --reload
- [ ] Open your browser at `http://127.0.0.1:8000/docs`
- [ ] Confirm `/health` returns `{"status": "ok"}`
- [ ] Confirm `/health/db` returns `{"status": "ok"}` — verifies database connection