# =========================================================
# AnalystStack — developer tasks (uv, Windows / PowerShell)
# =========================================================

SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command

UV := uv
PYTHON_VERSION := 3.13

# =========================================================
# Environment
# =========================================================

.PHONY: python
python:
	$(UV) python install $(PYTHON_VERSION)

.PHONY: sync
sync:
	$(UV) sync --all-extras

.PHONY: lock
lock:
	$(UV) lock

.PHONY: install
install: sync

# =========================================================
# Quality
# =========================================================

.PHONY: format
format:
	$(UV) run ruff format src/AnalystStack test

.PHONY: format-check
format-check:
	$(UV) run ruff format --check src/AnalystStack test

.PHONY: lint
lint:
	$(UV) run ruff check src/AnalystStack test --fix

.PHONY: typecheck
typecheck:
	$(UV) run mypy --ignore-missing-imports src/AnalystStack test

.PHONY: test
test:
	$(UV) run pytest

.PHONY: check
check: format-check lint typecheck test

# =========================================================
# Build / docs
# =========================================================

.PHONY: build
build: clean
	$(UV) build

.PHONY: docs
docs:
	$(UV) run zensical build --strict --clean

.PHONY: docs-serve
docs-serve:
	$(UV) run zensical serve

.PHONY: clean
clean:
	Remove-Item -Recurse -Force build, dist, *.egg-info, src/*.egg-info, site, .cache -ErrorAction SilentlyContinue
	Get-ChildItem -Recurse -Include __pycache__, .pytest_cache, .mypy_cache -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
