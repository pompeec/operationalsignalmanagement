.PHONY: install demo test interactive web help

help:
	@echo ""
	@echo "  Signal Detector — Noise vs Signal for Program Managers"
	@echo ""
	@echo "  make install      Install dependencies"
	@echo "  make demo         Run full demo against 12 mock PM scenarios (terminal)"
	@echo "  make test         Run a single quick classification (terminal)"
	@echo "  make interactive  Start interactive mode — paste items live (terminal)"
	@echo "  make web          Start the web UI at http://localhost:5000"
	@echo ""
	@echo "  Requires: ANTHROPIC_API_KEY in .env or environment"
	@echo ""

install:
	pip install -r requirements.txt

demo:
	python -m signal_detector.cli analyze examples/sample_inputs.json --show-noise

test:
	python -m signal_detector.cli analyze --text \
		"Payments service timing out for EU users since 14:47 UTC, 100% failure rate on checkout" \
		--source pagerduty

interactive:
	python -m signal_detector.cli interactive

web:
	python app.py
