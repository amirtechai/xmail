# Xmail Subject Line Generator Prompt v1

Generate **5 alternative subject lines** for a cold outreach email to the following contact.

## Contact

```json
{{ contact | tojson(indent=2) }}
```

## Email Body Summary

{{ body_summary }}

## Subject Line Rules

1. Maximum 8 words.
2. No spam trigger words: "free", "guaranteed", "limited time", "act now", "urgent", "100%".
3. No ALL CAPS.
4. No excessive punctuation or emojis.
5. Must feel personal and relevant to THEIR industry/role.
6. Vary the approach across the 5 options:
   - Option 1: Question-based
   - Option 2: Benefit-first
   - Option 3: Curiosity/intrigue
   - Option 4: Name/company mention
   - Option 5: Direct and specific

## Output Format

```json
[
  "Quick question about {{ contact.company }}'s partnerships",
  "How PriceONN reaches 2M+ traders monthly",
  "Something we noticed about your coverage",
  "{{ contact.company }} + PriceONN — worth 15 mins?",
  "Partnership proposal: financial services comparison"
]
```

Output ONLY valid JSON array of 5 strings.
