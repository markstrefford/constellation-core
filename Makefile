.PHONY: test lint install serve-supply-chain serve-stock-market viewer-build viewer-dev

install:
	pip install -e ".[dev,server]"
	cd viewer && npm install

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/ examples/

# Run simulations headless
run-supply-chain:
	python -m constellation_core run examples/supply_chain/config.yaml --ticks 200

run-stock-market:
	python -m constellation_core run examples/stock_market/config.yaml --ticks 200

# Build viewer
viewer-build:
	cd viewer && npx tsc && npx vite build

# Dev mode: run viewer dev server (proxy to backend on :8000)
viewer-dev:
	cd viewer && npx vite

# Serve with backend (start server, then open viewer dev server separately)
serve-supply-chain:
	python -m constellation_core serve examples/supply_chain/config.yaml

serve-stock-market:
	python -m constellation_core serve examples/stock_market/config.yaml
