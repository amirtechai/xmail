# Xmail Reply Classifier Prompt v1

Classify an email reply received in response to a cold outreach email from PriceONN.com.

## Original Email Subject

{{ original_subject }}

## Reply Content

```
{{ reply_text }}
```

## Classification Categories

Classify the reply into ONE of the following:

| Category | Description |
|----------|-------------|
| `positive_interest` | Recipient is interested, wants to know more or schedule a call |
| `meeting_request` | Recipient explicitly proposes a meeting/call time |
| `referral` | Recipient forwards to the right person or provides another contact |
| `not_interested` | Polite or direct decline |
| `out_of_office` | Auto-reply, vacation, or OOO message |
| `bounced` | Delivery failure notification |
| `unsubscribe_request` | Explicit request to stop emails |
| `question` | Recipient asks a clarifying question before deciding |
| `spam_complaint` | Recipient marks or reports as spam |
| `unknown` | Cannot determine intent |

## Output Format

```json
{
  "category": "positive_interest",
  "confidence": 0.92,
  "summary": "Recipient expressed interest in learning more about PriceONN's affiliate program",
  "suggested_action": "Schedule a 15-minute intro call within 24 hours",
  "sentiment": "positive",
  "urgency": "high"
}
```

`confidence` is a float from 0.0 to 1.0.
`sentiment`: `"positive"`, `"neutral"`, `"negative"`.
`urgency`: `"high"` (respond today), `"medium"` (respond within 48h), `"low"` (no rush).

Output ONLY valid JSON.
