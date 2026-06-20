.PHONY: run test security-scan security-scan-llm install

run:
	DATABASE_URL=sqlite+aiosqlite:///./popo.db uvicorn app.main:app --reload --port 8000

test:
	DATABASE_URL=sqlite+aiosqlite:///:memory: python3 -m pytest tests/ -v --asyncio-mode=auto

install:
	pip install -r requirements.txt

security-scan:
	@echo "Running SkillSpector static scan..."
	skillspector scan . --no-llm --format terminal
	@echo ""
	@echo "Saving markdown report..."
	skillspector scan . --no-llm --format markdown --output security-report.md || true

security-scan-llm:
	@echo "Running SkillSpector scan with LLM analysis (requires ANTHROPIC_API_KEY)..."
	SKILLSPECTOR_PROVIDER=anthropic skillspector scan . --format markdown --output security-report.md
