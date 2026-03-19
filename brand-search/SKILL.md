---
name: brand-search
description: "Fetch MR's assigned brands from Emcure API. Silent skill used by other modes to get product context. Falls back to previous month if current month data is incomplete."
metadata: {"openclaw": {"always": false, "silent": true}}
---

# Brand Search

Silent helper skill that fetches the MR's assigned brands from the Emcure API.

## When Called

- By `field-coaching` when preparing product recommendations
- By `objection-handler` when MR mentions a product objection
- By `product-deepdive` when starting a deep-dive session
- By `doctor-roleplay` when setting up product context for simulation

## Tool

```bash
python3 ~/.openclaw/workspace/scripts/emcure_api.py --query employee_brands --name "{MR_NAME}" --division "{DIVISION}" --hq "{HQ}"
```

## Fallback Logic

If current month returns empty brands (month in progress), automatically fetch from previous month:

```bash
python3 ~/.openclaw/workspace/scripts/emcure_api.py --query employee_brands --name "{MR_NAME}" --division "{DIVISION}" --hq "{HQ}" --month "February" --year "2026"
```

## Response Format

```json
{
  "status": "success",
  "result": [
    {"Brand": "DYDROFEM"},
    {"Brand": "FCMO"},
    {"Brand": "MVISTA"},
    {"Brand": "PAUSE"},
    {"Brand": "VICARE"}
  ]
}
```

## Usage in Conversation

Never mention brand fetching to the MR. Use the brands silently to:
- Recommend products for specific doctors
- Provide clinical talking points
- Handle objections for specific products
- Set up roleplay scenarios with realistic product context

## Brand → Use Case Mapping (Emcure Pharma portfolio)

| Brand | Generic | Therapeutic Area | Common Doctor Specialty |
|---|---|---|---|
| PAUSE | Medroxyprogesterone | AUB, DUB, menstrual disorders | Gynecologist |
| DYDROFEM | Dydrogesterone | Threatened abortion, luteal support | Gynecologist |
| FCMO | Iron + Folic Acid + Multivitamins | Anemia, pregnancy support | Gynecologist, GP |
| MVISTA | Multivitamins | General wellness, pregnancy | GP, Gynecologist |
| VICARE | Respiratory formulation | Cough, cold, respiratory infections | Chest Physician, GP |
| OROFER | Iron Sucrose / Iron supplements | Iron deficiency anemia | Gynecologist, Physician |

Use this mapping to match products to doctor specialties when coaching.
