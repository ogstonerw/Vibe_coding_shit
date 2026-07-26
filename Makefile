.PHONY: install-codex check test

install-codex:
	python3 scripts/install_codex_config.py

check:
	python3 scripts/self_check.py
	python3 -m unittest discover -s tests -v

test:
	python3 -m unittest discover -s tests -v

