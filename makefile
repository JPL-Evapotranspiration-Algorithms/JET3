# Define the package name, module name, environment name, and Python version
PACKAGE_NAME = JET3
MODULE_NAME = $(subst -,_,$(PACKAGE_NAME))
ENVIRONMENT_NAME = $(PACKAGE_NAME)
DOCKER_IMAGE_NAME = $(shell echo $(PACKAGE_NAME) | tr '[:upper:]' '[:lower:]')
PYTHON_VERSION = $(if $(PYTHON),$(PYTHON),3.13)

# Allow passing extra flags via command line: make <target> ARGS="-k test_name"
ARGS ?=

# Include a Makefile.local to override things, if found
-include Makefile.local

.DEFAULT_GOAL := help

.PHONY: help clean test verify wheel sdist build twine-upload dist \
        install uninstall reinstall environment remove-environment \
        generate-input-dataset generate-output-dataset generate-GEOS5FP-inputs \
        colima-start docker-build docker-build-environment docker-build-installation \
        docker-interactive docker-remove compile-documentation \
        repomix copy-notebooks pack-notebooks render-notebooks \
        generate-history show-issues

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}'

##@ Cleanup & Environment
clean: ## Remove build artifacts, caches, coverage files, and logs
	rm -rf *.o *.out *.log
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf htmlcov/ .coverage
	rm -rf $(PACKAGE_NAME)-repomix.xml repomix-output.xml repomix-notebooks.xml
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete

environment: ## Create a new Conda/Mamba environment (override with PYTHON=3.12)
	mamba create -y -n $(ENVIRONMENT_NAME) -c conda-forge python=$(PYTHON_VERSION)

remove-environment: ## Remove the Conda/Mamba environment
	mamba env remove -y -n $(ENVIRONMENT_NAME)

install: ## Install the package in editable mode with development dependencies
	pip install -e .[dev]

uninstall: ## Uninstall the package
	pip uninstall -y $(PACKAGE_NAME)

reinstall: ## Reinstall the package (uninstall and then install)
	$(MAKE) uninstall
	$(MAKE) install

##@ Testing & Verification
test: ## Run Python unit tests using pytest
	pytest -vv -p no:warnings $(ARGS)

verify: ## Run model verification against reference outputs
	python -c "from $(MODULE_NAME).verify import verify; exit(0 if verify() else 1)"

##@ Packaging & Release
wheel: ## Build the Python wheel
	python -m build --wheel

sdist: ## Build the Python source distribution
	python -m build --sdist

build: ## Build the Python wheel and source distribution
	python -m build

twine-upload: ## Upload the built package to PyPI using Twine
	twine upload dist/*

dist: ## Clean, build, and upload the package to PyPI
	$(MAKE) clean
	$(MAKE) build
	$(MAKE) twine-upload

##@ Data Generation
generate-input-dataset: ## Generate ECOv002 cal/val input dataset
	python -c "from $(MODULE_NAME).generate_input_dataset import generate_input_dataset; generate_input_dataset()"

generate-output-dataset: ## Generate ECOv002 cal/val output dataset
	python -c "from $(MODULE_NAME).generate_output_dataset import main; main()"

generate-GEOS5FP-inputs: ## Generate GEOS-5 FP input table
	python -c "from $(MODULE_NAME).generate_GEOS5FP_inputs import generate_GEOS5FP_inputs; generate_GEOS5FP_inputs()"

##@ Docker & Colima
colima-start: ## Start Colima with 16GB RAM, x86_64 architecture, and 100GB disk
	colima start -m 16 -a x86_64 -d 100

docker-build: ## Build the Docker image
	docker build -t $(DOCKER_IMAGE_NAME):latest .

docker-build-environment: ## Build the Docker image up to the 'environment' stage
	docker build --target environment -t $(DOCKER_IMAGE_NAME):latest .

docker-build-installation: ## Build the Docker image up to the 'installation' stage
	docker build --target installation -t $(DOCKER_IMAGE_NAME):latest .

docker-interactive: ## Run the Docker container interactively with Fish shell
	docker run -it $(DOCKER_IMAGE_NAME) fish

docker-remove: ## Forcefully remove the Docker image
	docker rmi -f $(DOCKER_IMAGE_NAME)

##@ Documentation & Notebooks
compile-documentation: ## Compile ATBD and User Guide from Markdown to PDF
	bash documentation/ECOv003_L3_L4_JET_ATBD.sh
	bash documentation/ECOv003_L3_L4_JET_User_Guide.sh

render-notebooks: ## Execute active notebooks in isolation and render PDFs
	python notebooks/render_notebooks.py

copy-notebooks: ## Pack stripped notebooks and copy to clipboard
	rm -rf /tmp/jet_nb
	mkdir -p /tmp/jet_nb
	python -c 'import glob, json, os; trim = lambda x: ("".join(x) if isinstance(x, list) else x)[:1500]; [json.dump({**nb, "cells": [{**c, "outputs": [{**o, **({"data": {"text/plain": trim(o["data"]["text/plain"])}} if "data" in o and "text/plain" in o["data"] else {"data": {}} if "data" in o else {}), **({"text": trim(o["text"])} if "text" in o else {})} for o in c.get("outputs", [])]} for c in nb.get("cells", [])]}, open(os.path.join("/tmp/jet_nb", os.path.basename(p)), "w")) for p in glob.glob("notebooks/*.ipynb") if not p.endswith("copy.ipynb") for nb in [json.load(open(p))]]'
	npx repomix /tmp/jet_nb --copy
	rm -rf /tmp/jet_nb repomix-output.xml

pack-notebooks: ## Pack stripped notebooks into repomix-notebooks.xml
	rm -rf /tmp/jet_nb
	mkdir -p /tmp/jet_nb
	python -c 'import glob, json, os; trim = lambda x: ("".join(x) if isinstance(x, list) else x)[:1500]; [json.dump({**nb, "cells": [{**c, "outputs": [{**o, **({"data": {"text/plain": trim(o["data"]["text/plain"])}} if "data" in o and "text/plain" in o["data"] else {"data": {}} if "data" in o else {}), **({"text": trim(o["text"])} if "text" in o else {})} for o in c.get("outputs", [])]} for c in nb.get("cells", [])]}, open(os.path.join("/tmp/jet_nb", os.path.basename(p)), "w")) for p in glob.glob("notebooks/*.ipynb") if not p.endswith("copy.ipynb") for nb in [json.load(open(p))]]'
	npx repomix /tmp/jet_nb -o repomix-notebooks.xml
	rm -rf /tmp/jet_nb

##@ Utilities
repomix: ## Pack repository context for LLM review
	npx repomix -o $(PACKAGE_NAME)-repomix.xml --ignore "**/*.csv,**/*.tsv,**/*.svg,**/*.egg-info/**,**/*.ipynb,*-repomix*.xml,repomix-output.xml,repomix-notebooks.xml,release_diffs.patch,LICENSE" --copy

generate-history: ## Generate release commit history patch
	fish -c ' \
		git fetch --tags --quiet; \
		set first_commit (git rev-list --max-parents=0 HEAD | head -n 1); \
		set releases (gh release list --limit 1000 --json tagName,createdAt --jq "sort_by(.createdAt) | .[].tagName"); \
		begin; \
			echo "========================================"; \
			echo "REPOSITORY RELEASE TIMELINE"; \
			echo "========================================"; \
			gh release list --limit 1000; \
			echo ""; \
			if test (count $$releases) -ge 1; \
				set first_rel $$releases[1]; \
				echo "========================================"; \
				echo "INITIAL COMMIT ($$first_commit) -> FIRST RELEASE ($$first_rel)"; \
				echo "========================================"; \
				git log --reverse --stat -p $$first_commit^..$$first_rel -- "*.py" "pyproject.toml"; \
				echo ""; \
			end; \
			if test (count $$releases) -ge 2; \
				for i in (seq 2 (count $$releases)); \
					set prev_idx (math $$i - 1); \
					set prev $$releases[$$prev_idx]; \
					set curr $$releases[$$i]; \
					echo "========================================"; \
					echo "RELEASE COMMIT HISTORY: $$prev -> $$curr"; \
					echo "========================================"; \
					git log --reverse --stat -p $$prev..$$curr -- "*.py" "pyproject.toml"; \
					echo ""; \
				end; \
			end; \
			if test (count $$releases) -ge 1; \
				set latest_rel $$releases[-1]; \
				echo "========================================"; \
				echo "LATEST RELEASE ($$latest_rel) -> CURRENT WORKING TREE (HEAD + UNCOMMITTED)"; \
				echo "========================================"; \
				git log --reverse --stat -p $$latest_rel..HEAD -- "*.py" "pyproject.toml"; \
				echo ""; \
				git status -s -- "*.py" "pyproject.toml"; \
				echo ""; \
				git diff HEAD -- "*.py" "pyproject.toml"; \
			else; \
				echo "========================================"; \
				echo "INITIAL COMMIT ($$first_commit) -> CURRENT WORKING TREE"; \
				echo "========================================"; \
				git log --reverse --stat -p -- "*.py" "pyproject.toml"; \
				echo ""; \
				git status -s -- "*.py" "pyproject.toml"; \
				echo ""; \
				git diff HEAD -- "*.py" "pyproject.toml"; \
			end; \
		end > release_diffs.patch; \
	'

show-issues: ## List open GitHub issues
	gh issue list --state open --json number,title,body --template '{{range .}}## #{{.number}}: {{.title}}{{"\n\n"}}{{.body}}{{"\n\n---\n\n"}}{{end}}'