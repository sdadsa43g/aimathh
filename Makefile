.PHONY: install dev test lint typecheck server web demos bench clean

install:
	pip install -e .

dev:
	pip install -e .[dev]

test:
	pytest tests/unit -q

test-all:
	pytest tests -q

bench:
	pytest tests/benchmarks -q

lint:
	ruff check src tests demos 2>/dev/null || echo "(ruff not installed)"

typecheck:
	mypy src/aimathh/core src/aimathh/math src/aimathh/physics src/aimathh/verification 2>/dev/null || echo "(mypy not installed)"

server:
	uvicorn aimathh.server.app:app --host 0.0.0.0 --port 8000 --reload

web:
	cd apps/web && npm install && npm run dev

demos:
	python demos/demo1_mechanics_derive_simulate.py
	python demos/demo2_ode_multi_method.py
	python demos/demo3_dimensional_reject.py
	python demos/demo4_counterexample.py

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; true
	rm -rf build dist *.egg-info htmlcov coverage .pytest_cache
