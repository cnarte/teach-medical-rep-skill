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

## Workflow

1. Get MR's name, division, and HQ from profile (memory or get_mr_profile)
2. Fetch brands for current month
3. If result is empty, retry with previous month
4. Use web_search to get clinical details for any brand the MR asks about

## Tool: Fetch Brands

```bash
python3 ~/.openclaw/workspace/scripts/emcure_api.py --query employee_brands --name "{MR_NAME}" --division "{DIVISION}" --hq "{HQ}"
```

## Fallback: Previous Month

If current month returns empty (month in progress):

```bash
python3 ~/.openclaw/workspace/scripts/emcure_api.py --query employee_brands --name "{MR_NAME}" --division "{DIVISION}" --hq "{HQ}" --month "{PREV_MONTH}" --year "{YEAR}"
```

## Response Format

```json
{
  "status": "success",
  "result": [
    {"Brand": "BRAND_NAME_1"},
    {"Brand": "BRAND_NAME_2"}
  ]
}
```

## Getting Brand Details

Once you have brand names, use web_search to find:
- Generic name / molecule
- Therapeutic area / indication
- Common prescribing specialties
- Clinical evidence / studies

```
web_search("{BRAND_NAME} {COMPANY} composition indication clinical use")
```

## Usage in Conversation

Never mention brand fetching to the MR. Use the brands silently to:
- Recommend products for specific doctors based on specialty
- Provide clinical talking points (fetched via web_search)
- Handle objections for specific products
- Set up roleplay scenarios with realistic product context

## Matching Brands to Doctors

After fetching brands, cross-reference with doctor's specialty from missed_doctors or doctor_visits:
1. Get doctor specialty from API
2. web_search for brand indications
3. Match brands to specialty (e.g., gynec products for gynecologist)
4. Coach MR on which brand to pitch to which doctor
