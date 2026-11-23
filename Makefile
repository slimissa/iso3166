# Makefile: one entry point for building and testing the ISO 3166 registry.
#
# Every command here already exists in scripts/release.sh or in the README's
# "Tests" table. The Makefile adds no step of its own; it names them.
#
#   make package           regenerate every committed artifact
#   make build-wheel       build the Python wheel and sdist (needs `build`)
#   make test              run every suite and the cross-language check
#   make registry-release  regenerate registry_release.json
#   make check             run every example and diff it against its pinned output
#
# Needs GNU make, python3, and for `make test` also node, cargo and go.

PYTHON   ?= python3
CURRENCY_SOURCE ?= iso4217.json

.DEFAULT_GOAL := help

.PHONY: help package build-wheel test registry-release check

help:
	@echo "targets: package build-wheel test registry-release check"
	@echo "see the README section 'Build and test with make'"

# The generators release.sh step 2 runs, in the same order, minus
# gen_registry_release (its own target) plus the ISO 4217 snapshot.
package:
	$(PYTHON) tools/export_sql.py
	$(PYTHON) tools/export_csv.py
	$(PYTHON) tools/export_parquet.py
	$(PYTHON) tools/export_aggregated.py
	$(PYTHON) tools/sync_wrappers.py
	$(PYTHON) tools/gen_consistency_fixture.py
	$(PYTHON) tools/gen_withdrawn_doc.py
	$(PYTHON) tools/gen_state_doc.py
	@if [ -f "$(CURRENCY_SOURCE)" ]; then \
		echo "$(PYTHON) tools/gen_iso4217_snapshot.py --source $(CURRENCY_SOURCE)"; \
		$(PYTHON) tools/gen_iso4217_snapshot.py --source "$(CURRENCY_SOURCE)"; \
	else \
		echo "skip: $(CURRENCY_SOURCE) not present, tools/iso4217_snapshot.json left as is"; \
	fi

# Needs the `build` package: pip install build
build-wheel:
	cd wrappers/python && $(PYTHON) -m build --wheel --sdist

test:
	$(PYTHON) -m pytest tests/ -q
	cd wrappers/python && $(PYTHON) -m pytest tests -q
	cd wrappers/javascript && npm test
	cd wrappers/rust && cargo test
	cd wrappers/go && go test ./...
	bash tools/check_cross_language.sh US GB JP

registry-release:
	$(PYTHON) tools/gen_registry_release.py

check:
	bash examples/run_all.sh --check
