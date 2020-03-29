PY := python3
PIP := pip3

PKG := zendown

.PHONY: help dev test tc lint fmt install clean

help:
	@echo "Targets:"
	@echo "help     show this help message"
	@echo "install  install zendown"
	@echo "dev      install in dev mode"
	@echo "test     run tests"
	@echo "tc       run typechecker"
	@echo "lint     run linter"
	@echo "fmt      format code"
	@echo "clean    clean output directories"

install:
	$(PIP) install .

dev:
	$(PIP) install -r requirements-dev.txt

test:
	$(PY) -m pytest

tc:
	$(PY) -m mypy $(PKG)

lint:
	$(PY) -m pylint $(PKG)

fmt:
	$(PY) -m black .

clean:
	rm -rf $(PKG).egg-info
	rm -rf .pytest_cache
	rm -rf $(PKG)/__pycache__
	rm -rf $(PKG)/*.pyc
