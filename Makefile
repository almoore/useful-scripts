.PHONY: install check uninstall help python-deps

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Create all ~/bin and dotfile symlinks
	./setup-symlinks.sh install

check: ## Show symlink status (dry run)
	./setup-symlinks.sh check -v

uninstall: ## Remove all managed symlinks
	./setup-symlinks.sh remove

list: ## List existing symlinks pointing to this repo
	./setup-symlinks.sh list

python-deps: ## Install Python dependencies
	pipenv install
	@echo ""
	@echo "Note: api-scripts also need: pip install -r api-scripts/requirements.txt"
