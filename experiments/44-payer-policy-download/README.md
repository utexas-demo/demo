# Experiment 44: Payer Policy Download — Anti-VEGF PA Rule Library

Downloads publicly available medical policy documents from 6 major payers to build a structured prior authorization rule library for anti-VEGF intravitreal injections.

## Payers

| Payer | Type | Key Documents |
|-------|------|---------------|
| CMS Medicare Traditional | FFS | LCDs, NCDs, ASP pricing |
| UnitedHealthcare | MA | Medical policies, PA list, formulary |
| Aetna | MA | Clinical Policy Bulletins, precertification |
| BCBS of Texas | Commercial + MA | Medical policies, PA requirements |
| Humana | MA | Coverage policies, PA lookup |
| Cigna | MA | Coverage policies, EviCore guidelines |

## Quick Start

```bash
# Install dependencies
pip install requests beautifulsoup4 pdfplumber pyyaml

# Download all payer policies
python download_policies.py

# Download specific payer(s)
python download_policies.py --payer cms_medicare uhc

# List configured payers
python download_policies.py --list

# Verify existing downloads
python download_policies.py --verify

# Extract structured rules from downloaded PDFs
python extract_rules.py

# View extraction summary
python extract_rules.py --summary
```

## Output Structure

```
data/
├── cms_medicare/     # CMS LCDs, NCDs, ASP pricing
├── uhc/              # UHC medical policies, PA requirements
├── aetna/            # Aetna CPBs, precertification
├── bcbstx/           # BCBSTX medical policies
├── humana/           # Humana coverage policies
├── cigna/            # Cigna + EviCore guidelines
└── manifest.json     # Download manifest (URLs, dates, SHA-256 checksums)

rules/
└── payer_rules.json  # Extracted structured PA rules
```

## Manifest

Every download is tracked in `data/manifest.json` with:
- Source URL
- Download timestamp
- File size
- SHA-256 checksum
- Content type
- Status (success/failed)

Run `python download_policies.py --verify` to validate all files against the manifest.

## Rule Schema

Each rule represents one **payer × drug × diagnosis** combination. The extractor reads each downloaded PDF, checks if it mentions any target drugs (by HCPCS code, generic name, or brand name), and for each drug × diagnosis pair found, creates a rule object with evidence extracted via regex patterns.

### How Rules Are Generated

```
PDF document
  → text extraction (pdfplumber)
  → relevance check (mentions any target drug/procedure?)
  → pattern matching (PA required? step therapy? documentation? denial triggers?)
  → cross with drugs × diagnoses mentioned in the text
  → one rule per (payer, drug, diagnosis) combination
```

A single PDF that mentions 3 drugs and 2 diagnoses produces 6 rules. Each rule carries its own evidence lines — the specific text excerpts that matched the regex patterns.

### Field Reference

```json
{
  "payer_id": "uhc",
  "payer_name": "UnitedHealthcare Medicare Advantage",
  "drug_code": "J0178",
  "drug_name": "Eylea (aflibercept)",
  "procedure_code": "67028",
  "diagnosis_group": "wet_amd",
  "covered_icd10": ["H35.31", "H35.32"],
  "pa_required": true,
  "pa_evidence": ["Prior authorization required. Prior authorization is required for all states."],
  "step_therapy_required": true,
  "step_therapy_evidence": ["Must try bevacizumab first before aflibercept"],
  "required_documentation": ["OCT within 30 days", "Visual acuity"],
  "auth_duration_months": 6,
  "auth_max_injections": 12,
  "denial_triggers": ["Missing documentation", "Expired authorization"],
  "hcpcs_codes_found": ["J0178", "J9035", "J2778"],
  "policy_source_file": "data/uhc/UHC_Medicare_Advantage_PA_Requirements_Mar2026.pdf",
  "policy_last_downloaded": "2026-03-07",
  "extraction_confidence": "high"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `payer_id` | string | Config key for the payer (e.g., `uhc`, `aetna`, `cms_medicare`) |
| `payer_name` | string | Human-readable payer name from config |
| `drug_code` | string | HCPCS J-code for the drug (e.g., `J0178`). Set to `GENERIC` if the document discusses anti-VEGF agents without naming specific drugs |
| `drug_name` | string | Brand and generic name, formatted as `Brand (generic)` |
| `procedure_code` | string | CPT code if `67028` (intravitreal injection) appears in the document; empty string otherwise |
| `diagnosis_group` | string | One of: `wet_amd`, `dme` (diabetic macular edema), `rvo` (retinal vein occlusion), `geographic_atrophy`, or `general_ophthalmology` (fallback when no specific ICD-10 codes are found) |
| `covered_icd10` | string[] | ICD-10 codes found in the document that match the diagnosis group's patterns. For `general_ophthalmology`, includes up to 20 ICD-10 codes found anywhere in the text |
| `pa_required` | bool | `true` if any PA-related pattern matched (e.g., "prior authorization required", "precertification required") |
| `pa_evidence` | string[] | Up to 5 text lines that matched PA patterns — the raw evidence supporting `pa_required` |
| `step_therapy_required` | bool | `true` if step therapy patterns matched (e.g., "must try bevacizumab first", "preferred agent") |
| `step_therapy_evidence` | string[] | Up to 5 text lines that matched step therapy patterns |
| `required_documentation` | string[] | Up to 10 unique text lines matching documentation patterns (e.g., "OCT within 30 days", "visual acuity", "letter of medical necessity") |
| `auth_duration_months` | int \| null | Number of months the authorization is valid, if found in text |
| `auth_max_injections` | int \| null | Maximum number of injections authorized per approval period, if found |
| `denial_triggers` | string[] | Up to 10 text lines matching denial patterns (e.g., "missing documentation", "expired authorization", "wrong diagnosis") |
| `hcpcs_codes_found` | string[] | All HCPCS J-codes found anywhere in the document (not just target drugs — useful for cross-referencing) |
| `policy_source_file` | string | Path to the PDF that this rule was extracted from |
| `policy_last_downloaded` | string | ISO date when the source PDF was last downloaded |
| `extraction_confidence` | string | See [Confidence Levels](#confidence-levels) below |

### Confidence Levels

| Level | Criteria | What It Means |
|-------|----------|---------------|
| **high** | 2+ PA pattern matches **and** 1+ step therapy match | The document has strong, specific language about both prior authorization requirements and step therapy for this drug. Most actionable — safe to build automation rules from. |
| **medium** | 1+ PA pattern match, no step therapy match | The document mentions PA requirements but doesn't discuss step therapy (or the extractor didn't find step therapy language). Likely accurate for PA status, but may be missing step therapy details. |
| **low** | Drug mentioned but no PA patterns matched | The drug appears in the document, but no PA-specific language was found near it. The rule exists because the document is relevant, but we can't confirm whether PA is actually required. Treat as informational only. |

**Why are most rules medium or low?** The current downloaded PDFs are broad PA requirement lists covering hundreds of drugs and procedures. The PA language found is generic to the whole document (e.g., "precertification is required for the Aetna Medicare" at the top of a 50-page list) rather than drug-specific criteria. The payer-specific clinical policy bulletins (Aetna CPBs, EviCore ophthalmology guidelines) that contain drug-specific PA criteria require Playwright to download from JS-rendered pages — once those are added, expect more high-confidence rules.

### How Fields Interact

- **`pa_required` ↔ `pa_evidence`**: `pa_required` is `true` when `pa_evidence` is non-empty. The evidence lines are the proof — if they look like false positives (e.g., PA text for a different drug), the rule's confidence is suspect.
- **`step_therapy_required` ↔ `step_therapy_evidence`**: Same relationship. Step therapy typically means the payer requires trying a cheaper drug (usually bevacizumab/Avastin) before approving the requested drug.
- **`extraction_confidence`**: Derived from the combination of `pa_evidence` and `step_therapy_evidence` counts. A `low` confidence rule means the drug was mentioned in the document but no PA-specific language was found near it — the rule still exists because the document is relevant, but the PA status is uncertain.
- **`diagnosis_group` ↔ `covered_icd10`**: The diagnosis group determines which ICD-10 pattern to filter by. When the extractor can't match specific diagnosis codes, it falls back to `general_ophthalmology` and includes all ICD-10 codes found in the document (up to 20).
- **`hcpcs_codes_found` vs `drug_code`**: `drug_code` is the specific drug this rule is about. `hcpcs_codes_found` is every J-code in the entire document — useful for seeing what else the policy covers alongside the target drug.
- **`auth_duration_months` ↔ `auth_max_injections`**: These are independent — a policy might authorize 6 months or 12 injections (whichever comes first). Both can be `null` if the document doesn't specify limits.

## Rebuild on New Machine

```bash
cd experiments/44-payer-policy-download
pip install requests beautifulsoup4 pdfplumber pyyaml
python download_policies.py
python extract_rules.py
```

## Notes

- Some payer portals use JavaScript rendering — if pages download as empty HTML, use Playwright fallback
- Only publicly accessible documents are downloaded (no login-walled content)
- Policy documents should be re-downloaded monthly to catch updates
- The `data/` directory is gitignored; use `download_policies.py` to rebuild
