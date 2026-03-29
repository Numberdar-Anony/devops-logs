PYTHON=.venv/bin/python
PIP=.venv/bin/pip
UVICORN=.venv/bin/uvicorn

setup:
	python3 -m venv .venv || true
	. .venv/bin/activate && $(PIP) install -r requirements.txt

run:
	. .venv/bin/activate && DATABASE_URL=sqlite+aiosqlite:///./devops_logs.db OLLAMA_BASE_URL=http://127.0.0.1:11434 OLLAMA_MODEL=qwen2.5-coder:7b $(UVICORN) app.main:app --reload

test:
	. .venv/bin/activate && DATABASE_URL=sqlite+aiosqlite:///./devops_logs.db python -m pytest -q

.PHONY: setup run test
