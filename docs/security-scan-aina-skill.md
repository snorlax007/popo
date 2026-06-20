# SkillSpector Security Report

**Skill:** AiNa App Factory — build  
**Source:** `/home/oc/.claude/skills/aina-skill`  
**Scanned:** 2026-06-20 07:26:45 UTC  

## Risk Assessment

| Metric | Value |
|--------|-------|
| Score | 100/100 |
| Severity | CRITICAL |
| Recommendation | DO NOT INSTALL |

## Components (63)

| File | Type | Lines | Executable |
|------|------|-------|------------|
| `SKILL.md` | markdown | 144 | No |
| `personas/braindoc/01-frame-investigator.md` | markdown | 53 | No |
| `personas/braindoc/02-user-mapper.md` | markdown | 49 | No |
| `personas/braindoc/03-scope-definer.md` | markdown | 54 | No |
| `personas/braindoc/04-roi-estimator.md` | markdown | 58 | No |
| `personas/braindoc/05-risk-mapper.md` | markdown | 52 | No |
| `personas/braindoc/06-milestone-planner.md` | markdown | 59 | No |
| `personas/braindoc/07-braindoc-writer.md` | markdown | 100 | No |
| `personas/dev/01-scaffolder.md` | markdown | 198 | No |
| `personas/dev/02-backend-builder.md` | markdown | 150 | No |
| `personas/dev/03-frontend-builder.md` | markdown | 238 | No |
| `personas/dev/04-test-writer.md` | markdown | 89 | No |
| `personas/dev/05-qa-reviewer.md` | markdown | 91 | No |
| `personas/dev/06-roadmap-planner.md` | markdown | 116 | No |
| `personas/docs/01-architecture-diagrammer.md` | markdown | 56 | No |
| `personas/docs/02-api-reference-writer.md` | markdown | 79 | No |
| `personas/docs/03-user-guide-writer.md` | markdown | 68 | No |
| `personas/docs/04-developer-guide-writer.md` | markdown | 92 | No |
| `personas/docs/05-docs-synthesizer.md` | markdown | 85 | No |
| `personas/ideation/01-domain-architect.md` | markdown | 51 | No |
| `personas/ideation/02-stack-selector.md` | markdown | 75 | No |
| `personas/ideation/03-data-modeler.md` | markdown | 62 | No |
| `personas/ideation/04-api-designer.md` | markdown | 69 | No |
| `personas/ideation/05-ux-composer.md` | markdown | 66 | No |
| `personas/ideation/06-nfr-specialist.md` | markdown | 68 | No |
| `personas/ideation/07-prd-synthesizer.md` | markdown | 85 | No |
| `personas/intent/01-domain-analyst.md` | markdown | 40 | No |
| `personas/intent/02-scope-architect.md` | markdown | 44 | No |
| `personas/intent/03-impact-quantifier.md` | markdown | 45 | No |
| `personas/intent/04-longevity-critic.md` | markdown | 46 | No |
| `personas/intent/05-dependency-mapper.md` | markdown | 47 | No |
| `personas/intent/06-variant-designer.md` | markdown | 64 | No |
| `personas/marketing/01-brand-strategist.md` | markdown | 65 | No |
| `personas/marketing/02-copywriter.md` | markdown | 119 | No |
| `personas/marketing/03-visual-designer.md` | markdown | 87 | No |
| `personas/marketing/04-marketing-pack-writer.md` | markdown | 79 | No |
| `personas/ops/01-deployment-planner.md` | markdown | 80 | No |
| `personas/ops/02-monitoring-designer.md` | markdown | 78 | No |
| `personas/ops/03-runbook-writer.md` | markdown | 82 | No |
| `personas/ops/04-ops-synthesizer.md` | markdown | 136 | No |
| `personas/readiness/01-deploy-assessor.md` | markdown | 60 | No |
| `personas/readiness/02-onboarding-reviewer.md` | markdown | 66 | No |
| `personas/readiness/03-cost-modeler.md` | markdown | 65 | No |
| `personas/readiness/04-dr-planner.md` | markdown | 72 | No |
| `personas/readiness/05-readiness-synthesizer.md` | markdown | 67 | No |
| `personas/security/01-threat-modeler.md` | markdown | 52 | No |
| `personas/security/02-dependency-auditor.md` | markdown | 59 | No |
| `personas/security/03-code-scanner.md` | markdown | 71 | No |
| `personas/security/04-security-synthesizer.md` | markdown | 71 | No |
| `scripts/classify_stack.py` | python | 70 | Yes |
| `scripts/package_output.py` | python | 76 | Yes |
| `scripts/seed_starter.py` | python | 62 | Yes |
| `starters/fastapi-htmx/Dockerfile` | other | 15 | No |
| `starters/fastapi-htmx/README.md` | markdown | 36 | No |
| `starters/fastapi-htmx/app/main.py` | python | 123 | Yes |
| `starters/fastapi-htmx/requirements.txt` | text | 4 | No |
| `starters/fastapi-htmx/static/css/app.css` | other | 268 | No |
| `starters/fastapi-htmx/static/js/htmx.min.js` | javascript | 1 | Yes |
| `starters/fastapi-htmx/templates/base.html` | other | 68 | No |
| `starters/fastapi-htmx/templates/pages/dashboard.html` | other | 57 | No |
| `starters/fastapi-htmx/templates/pages/items.html` | other | 44 | No |
| `starters/fastapi-htmx/templates/pages/roadmap.html` | other | 30 | No |
| `starters/fastapi-htmx/templates/partials/item_row.html` | other | 15 | No |

## Issues (10)

### 🟡 MEDIUM: AST4

**Location:** `scripts/package_output.py:20`  
**Confidence:** 70%  

**Message:** subprocess module call

**Remediation:** Use subprocess.run() with shell=False and an explicit argument list. Validate all inputs and avoid passing user-controlled data to commands.

---

### 🟡 MEDIUM: LP3

**Location:** `SKILL.md:1`  
**Confidence:** 70%  

**Message:** Skill has no declared permissions but code capabilities were detected: env, file_write, network, shell.

**Remediation:** Add a 'permissions' field to SKILL.md listing the capabilities this skill requires.

---

### 🟡 MEDIUM: EA2

**Location:** `personas/dev/05-qa-reviewer.md:23`  
**Confidence:** 85%  

**Message:** Autonomous Decision Making

**Remediation:** Add human-in-the-loop confirmation for destructive, irreversible, or high-impact operations. Never auto-execute commands that modify files, send data, or alter system state.

---

### 🟡 MEDIUM: EA2

**Location:** `personas/ideation/03-data-modeler.md:49`  
**Confidence:** 75%  

**Message:** Autonomous Decision Making

**Remediation:** Add human-in-the-loop confirmation for destructive, irreversible, or high-impact operations. Never auto-execute commands that modify files, send data, or alter system state.

---

### 🔴 HIGH: PE3

**Location:** `scripts/seed_starter.py:23`  
**Confidence:** 60%  

**Message:** Credential Access

**Remediation:** Remove references to credential paths. Use environment variables or secrets managers. For docs, use placeholder paths (e.g., /path/to/config). Never load .env or token files in production code paths.

---

### 🟡 MEDIUM: RA2

**Location:** `SKILL.md:4`  
**Confidence:** 60%  

**Message:** Session Persistence

**Remediation:** Remove any persistence mechanisms (cron jobs, startup scripts, state files). Skills should not maintain state across sessions without explicit user consent.

---

### 🟢 LOW: SC4

**Location:** `starters/fastapi-htmx/requirements.txt:3`  
**Confidence:** 60%  

**Message:** Known Vulnerable Dependency: jinja2==3.1.5 — 1 advisory(ies): CVE-2025-27516 (Jinja2 vulnerable to sandbox breakout through attr filter selecting format metho)

**Remediation:** Update the dependency to a patched version that addresses the known CVE. Check OSV (osv.dev) or NVD for details on the vulnerability.

---

### 🔴 HIGH: SC4

**Location:** `starters/fastapi-htmx/requirements.txt:4`  
**Confidence:** 80%  

**Message:** Known Vulnerable Dependency: python-multipart==0.0.20 — 7 advisory(ies): CVE-2026-53539 (python-multipart: Quadratic-time querystring parsing with semicolon separators c); CVE-2026-53538 (python-multipart: Semicolon treated as querystring field separator enables param); CVE-2026-40347 (python-multipart affected by Denial of Service via large multipart preamble or e) +4 more

**Remediation:** Update the dependency to a patched version that addresses the known CVE. Check OSV (osv.dev) or NVD for details on the vulnerability.

---

### 🔴 HIGH: SC6

**Location:** `starters/fastapi-htmx/requirements.txt:2`  
**Confidence:** 70%  

**Message:** Possible Typosquatting: 'uvicorn' resembles popular package 'gunicorn'

**Remediation:** Verify the package name is correct and not a typosquatting variant. Compare against the official package name on PyPI or npm.

---

### 🔴 HIGH: TM1

**Location:** `personas/ideation/04-api-designer.md:29`  
**Confidence:** 80%  

**Message:** Tool Parameter Abuse

**Remediation:** Validate all tool parameters against an allowlist. Reject dangerous parameter values (shell=True, --force, -rf /) and use safe defaults.

---

## Metadata

- **Executable Scripts:** Yes

*Generated by SkillSpector v2.2.3*