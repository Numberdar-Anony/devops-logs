PYTHON=.venv/bin/python
PIP=.venv/bin/pip
UVICORN=.venv/bin/uvicorn

setup:
	python3 -m venv .venv || true
	. .venv/bin/activate && $(PIP) install -r requirements.txt

run:
	. .venv/bin/activate && DATABASE_URL=sqlite+aiosqlite:///./devops_logs.db OPENROUTER_API_KEY=$$(grep OPENROUTER_API_KEY .env | cut -d '=' -f2) OPENROUTER_MODEL=openrouter/free $(UVICORN) app.main:app --reload

test:
	. .venv/bin/activate && DATABASE_URL=sqlite+aiosqlite:///./devops_logs.db python -m pytest -q

.PHONY: setup run test
