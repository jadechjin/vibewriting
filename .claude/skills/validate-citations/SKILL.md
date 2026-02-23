---
name: validate-citations
description: Validate citation integrity using checkcites on LaTeX aux files
---

# Citation Validation

Run checkcites to verify citation integrity between LaTeX source and BibTeX database.

## Prerequisites

- TeX Live must be installed (checkcites is part of TeX Live).
- The paper must have been compiled at least once (to generate `paper/build/main.aux`).

## Workflow

1. **Check prerequisites:**
   - Verify `checkcites` is available: `which checkcites`
   - Verify aux file exists: `paper/build/main.aux`

2. **Run checkcites:**
   ```bash
   checkcites paper/build/main.aux
   ```

3. **Interpret results:**
   - **Unused references**: Entries in `.bib` not cited in the paper. Consider removing them.
   - **Undefined references**: Citations in `.tex` not found in `.bib`. These must be fixed.

4. **Report to user:**
   - List any undefined references (critical: will cause compilation warnings).
   - List any unused references (informational: clean up if desired).
   - Suggest fixes for each issue found.

## Fallback

If TeX Live is not installed, report: "checkcites requires TeX Live. Install TeX Live to enable citation validation."
