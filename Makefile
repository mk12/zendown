.PHONY: help dev test fmt install clean

help:
	@echo "Targets:"
	@echo "help     show this help message"
	@echo "install  install zendown"
	@echo "dev      install in dev mode"
	@echo "test     run tests"
	@echo "fmt      format code"
	@echo "clean    clean output directories"

install:
	pip3 install .

dev:
	pip3 install -r requirements-dev.txt

test:
	python3 -m pytest

fmt:
	python3 -m black .

clean:
	rm -rf zendown.egg-info
	rm -rf __pycache__
	rm -rf .pytest_cache
