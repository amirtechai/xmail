# Xmail — Post-Phase-25 Feature Backlog
# Kaldığın yerden devam etmek için bu dosyayı oku.
# Her feature tamamlandığında [ ] → [x] yap.

## Durum Özeti
- Başlangıç: 2026-04-22
- Son güncelleme: 2026-04-24
- Tamamlanan: 6/12

---

## A — Domain Pattern Inference [x]
**Dosyalar:**
- `backend/app/agents/nodes/infer_email_pattern.py` (YENİ)
- `backend/app/agents/graph.py` (güncelle — yeni node ekle)
- `backend/app/agents/state.py` (güncelle — `inferred_emails` field)

**Ne yapılacak:**
1. Mevcut validated contact listesinden `{local}@{domain}` pattern analizi
2. Ortak format tespit: `first.last`, `flast`, `firstl`, `first_last`, vb.
3. Yeni prospect için pattern uygula → candidate email üret
4. Üretilen email'leri validate_email_node'a sok
5. Agent graph'a node ekle (score_contact'tan sonra)

---

## B — CSV / Excel Import Endpoint [x]
**Dosyalar:**
- `backend/app/api/routes/contacts.py` (güncelle)
- `backend/app/schemas/contact.py` (güncelle)
- `frontend/src/pages/ContactsPage.tsx` (güncelle)
- `backend/pyproject.toml` (openpyxl ekle)

**Ne yapılacak:**
1. `POST /api/contacts/import` — multipart CSV veya XLSX
2. Validation pipeline + duplicate check
3. Batch upsert, response: `{imported, skipped, errors}`
4. Frontend: drag-drop upload + sonuç modal

---

## C — Bulk Email Verification (ZeroBounce API) [x]
**Dosyalar:**
- `backend/app/email_validator/zerobounce_client.py` (YENİ)
- `backend/app/email_validator/validator.py` (güncelle)
- `backend/app/config.py` (ZEROBOUNCE_API_KEY)
- `backend/app/api/routes/contacts.py` (bulk verify endpoint)

**Ne yapılacak:**
1. ZeroBounceClient single + bulk verify
2. validator.py'ye ZeroBounce provider ekle
3. `POST /api/contacts/verify-bulk` → Celery kuyruğu
4. API key yoksa in-house fallback

---

## D — Follow-up Sequence (Drip Campaign) [x]
**Dosyalar:**
- `backend/app/models/campaign_sequence.py` (YENİ)
- `backend/app/models/campaign_sequence_step.py` (YENİ)
- `backend/app/api/routes/campaigns.py` (güncelle)
- `backend/app/schemas/campaign.py` (güncelle)
- `backend/app/tasks/sequence_runner.py` (YENİ)
- `backend/migrations/` (alembic revision)
- `frontend/src/pages/CampaignDetailPage.tsx` (sequence builder)

**Ne yapılacak:**
1. CampaignSequence + CampaignSequenceStep model
2. SentEmail'e sequence_step_id FK
3. Daily Celery task: gönderilmemiş step'leri gönder
4. Stop condition: reply gelirse durdur
5. Frontend: step builder UI

---

## E — Hunter.io Integration [x]
**Dosyalar:**
- `backend/app/scrapers/hunter_client.py` (YENİ)
- `backend/app/agents/nodes/hunter_lookup.py` (YENİ)
- `backend/app/agents/graph.py` (güncelle)
- `backend/app/config.py` (HUNTER_API_KEY)

**Ne yapılacak:**
1. HunterClient.domain_search + email_finder
2. hunter_lookup_node — company/website olan contact'lara uygula
3. API key yoksa node skip

---

## F — RSS Feed Scraper Node [x]
**Dosyalar:**
- `backend/app/agents/nodes/rss_feed_reader.py` (YENİ)
- `backend/app/agents/graph.py` (güncelle)
- `backend/app/tasks/rss_scraping_task.py` (YENİ)
- `backend/pyproject.toml` (feedparser)

**Ne yapılacak:**
1. rss_feed_reader_node — feedparser ile parse
2. Email extraction pipeline'a URL olarak sok
3. ScrapingSource'tan rss tiplerini çek
4. Günlük Celery beat task

---

## G — Email Preview / Test Send [ ]
**Dosyalar:**
- `backend/app/api/routes/campaigns.py` (preview endpoint)
- `frontend/src/pages/CampaignDetailPage.tsx` (test send butonu)

**Ne yapılacak:**
1. `POST /api/campaigns/{id}/preview` body: `{email}`
2. Template render + gerçek SMTP gönderim
3. Frontend: modal + email input

---

## H — Spam Score Checker [ ]
**Dosyalar:**
- `backend/app/core/spam_checker.py` (YENİ)
- `backend/app/api/routes/campaigns.py` (spam-check endpoint)
- `frontend/src/components/SpamScoreWidget.tsx` (YENİ)

**Ne yapılacak:**
1. Postmark spamcheck API entegrasyonu
2. `POST /api/campaigns/{id}/spam-check`
3. Frontend: renk kodlu score badge

---

## I — A/B Subject Line Testing [ ]
**Dosyalar:**
- `backend/app/models/campaign.py` (ab_enabled, subject_b)
- `backend/app/models/sent_email.py` (ab_variant)
- `backend/app/api/routes/campaigns.py` (güncelle)
- `frontend/src/pages/CampaignDetailPage.tsx` (A/B UI)

**Ne yapılacak:**
1. Campaign'e ab_enabled + subject_b field
2. Send logic: 50/50 split
3. Stats'a A/B karşılaştırma
4. Frontend: toggle + chart

---

## J — LinkedIn Enrichment (Proxycurl API) [ ]
**Dosyalar:**
- `backend/app/scrapers/proxycurl_client.py` (YENİ)
- `backend/app/agents/nodes/linkedin_enrich.py` (YENİ)
- `backend/app/agents/graph.py` (güncelle)
- `backend/app/config.py` (PROXYCURL_API_KEY)
- `backend/app/tasks/linkedin_enrichment_task.py` (YENİ)

**Ne yapılacak:**
1. ProxycurlClient.get_person(linkedin_url)
2. Selektif: sadece score>60 + linkedin_url dolu contact'lar
3. Günlük background task
4. API key yoksa skip

---

## K — RBAC (Viewer / Operator Rolleri) [ ]
**Dosyalar:**
- `backend/app/models/user.py` (UserRole enum güncelle)
- `backend/app/api/deps.py` (role check helpers)
- `backend/app/api/routes/*.py` (role dependency)
- `backend/migrations/` (alembic revision)
- `frontend/src/store/authStore.ts` (role-based UI)

**Ne yapılacak:**
1. UserRole: ADMIN, OPERATOR, VIEWER
2. require_role(min_role) dependency factory
3. Route'lara rol kontrolü ekle
4. Frontend: role'e göre UI gizle

---

## L — Webhook Receiver (Bounce/Open/Click) [ ]
**Dosyalar:**
- `backend/app/api/routes/webhooks.py` (YENİ)
- `backend/app/tasks/webhook_processor.py` (YENİ)
- `backend/app/models/sent_email.py` (opened_at, clicked_at)
- `backend/app/main.py` (router ekle)
- `backend/app/core/webhook_signatures.py` (YENİ)

**Ne yapılacak:**
1. SendGrid / Postmark / Mailgun webhook endpoint'leri
2. HMAC signature doğrulama
3. bounce → suppression; open/click → sent_email güncelle
4. Celery async işleme

---

## Tamamlanan Features
_(tamamlandıkça buraya taşı)_
