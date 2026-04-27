# Xmail — Post-Phase-25 Feature Backlog
# Kaldığın yerden devam etmek için bu dosyayı oku.
# Her feature tamamlandığında [ ] → [x] yap.

## Durum Özeti
- Başlangıç: 2026-04-22
- Son güncelleme: 2026-04-27
- Tamamlanan: 23/26

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

## G — Email Preview / Test Send [x]
**Dosyalar:**
- `backend/app/api/routes/campaigns.py` (preview endpoint)
- `frontend/src/pages/CampaignDetailPage.tsx` (test send butonu)

**Ne yapılacak:**
1. `POST /api/campaigns/{id}/preview` body: `{email}`
2. Template render + gerçek SMTP gönderim
3. Frontend: modal + email input

---

## H — Spam Score Checker [x]
**Dosyalar:**
- `backend/app/core/spam_checker.py` (YENİ)
- `backend/app/api/routes/campaigns.py` (spam-check endpoint)
- `frontend/src/components/SpamScoreWidget.tsx` (YENİ)

**Ne yapılacak:**
1. Postmark spamcheck API entegrasyonu
2. `POST /api/campaigns/{id}/spam-check`
3. Frontend: renk kodlu score badge

---

## I — A/B Subject Line Testing [x]
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

## J — LinkedIn Enrichment (Proxycurl API) [x]
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

## K — RBAC (Viewer / Operator Rolleri) [x]
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

## L — Webhook Receiver (Bounce/Open/Click) [x]
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

---

## M — Open Tracking Pixel [x]
**Dosyalar:**
- `backend/app/api/routes/tracking.py` (YENİ)
- `backend/app/main.py` (router ekle)

**Ne yapılacak:**
1. `GET /t/o/{sent_email_id}.gif` → 1×1 transparent GIF döndür
2. İlk açılışta `tracking_pixel_opened_at` set, status → OPENED
3. İkinci açılışta commit yok (idempotent)
4. `Cache-Control: no-store` header

---

## N — Unsubscribe Landing Page [x]
**Dosyalar:**
- `backend/app/api/routes/unsubscribe.py` (yeniden yaz)
- `backend/app/models/suppression_list.py` (güncelle)

**Ne yapılacak:**
1. `GET /u/{token}` → dark-themed HTML confirm page
2. `POST /u/{token}` → SuppressionList'e ekle, status → UNSUBSCRIBED
3. Zaten suppressed ise duplicate ekleme
4. BOUNCED status'u değiştirme

---

## O — Daily Digest Email Delivery [x]
**Dosyalar:**
- `backend/app/tasks/daily_report_delivery.py` (güncelle)
- `backend/app/sender/smtp_client.py` (var)

**Ne yapılacak:**
1. Günlük raporu hesapla (open/click rate dahil)
2. Tüm admin kullanıcılara dark-themed HTML digest gönder
3. SMTPClient ile ilk aktif SMTP konfigürasyonu kullan
4. Per-recipient hata handling, başarı sayısı döndür

---

## ★ P — Apollo.io Integration [ÖNCELIK] [x]
**Dosyalar:**
- `backend/app/scrapers/apollo_client.py` (YENİ)
- `backend/app/agents/nodes/apollo_lookup.py` (YENİ)
- `backend/app/agents/graph.py` (güncelle)
- `backend/app/config.py` (APOLLO_API_KEY)

**Ne yapılacak:**
1. ApolloClient — `POST /people/search` (industry, title, company filters)
2. Finance filter presets: hedge fund, private equity, investment banking, asset management
3. apollo_lookup_node — graph'a hunter'dan önce ekle
4. Dönen kişileri Contact olarak persist et (email doğrulanmış)
5. API key yoksa node skip

---

## ★ Q — Finance-Specific Data Sources [x]
**Dosyalar:**
- `backend/app/scrapers/sec_edgar_client.py` (YENİ)
- `backend/app/scrapers/finance_directories.py` (YENİ)
- `backend/app/tasks/finance_source_seeder.py` (YENİ)

**Ne yapılacak:**
1. SEC EDGAR company filings → contact name extraction
2. CFA Institute member directory scraper
3. Financial association directories (SIFMA, AIMA, MFA)
4. ScrapingSource'a pre-seed finance URLs
5. Domain list: gs.com, jpmchase.com, blackrock.com, vanguard.com, fidelity.com, citadel.com vb.

---

## ★ R — Finance-Targeted Planner Prompts [x]
**Dosyalar:**
- `backend/app/agents/nodes/planner.py` (güncelle)
- `backend/app/agents/state.py` (industry_vertical field)

**Ne yapılacak:**
1. `industry_vertical = "finance"` → özel prompt template
2. Finance-specific arama terimleri: "hedge fund manager email", "CFO investment bank contact"
3. Target titles: CFA, CFO, Portfolio Manager, Managing Director, VP Finance
4. Target firms: büyük bankalar, hedge fund'lar, PE firmaları, asset manager'lar
5. SerpAPI sorgularına site: filtresi ekle (linkedin.com/in, bloomberg.com)

---

## ★ S — Domain Bulk Email Generation [x]
**Dosyalar:**
- `backend/app/tasks/domain_bulk_targeting.py` (YENİ)
- `backend/app/scrapers/hunter_client.py` (domain_search bulk)
- `backend/app/agents/nodes/infer_email_pattern.py` (güncelle)

**Ne yapılacak:**
1. Finance firm domain listesi tanımla (config veya DB'de)
2. Hunter domain_search → tüm bilinen email'leri çek
3. infer_email_pattern ile `{first}.{last}@domain` üret
4. Validate + score → persist
5. Günlük Celery beat task

---

## T — People Data Labs (PDL) Integration [x]
**Dosyalar:**
- `backend/app/scrapers/pdl_client.py` (YENİ)
- `backend/app/agents/nodes/pdl_enrich.py` (YENİ)
- `backend/app/agents/graph.py` (güncelle)
- `backend/app/config.py` (PDL_API_KEY)

**Ne yapılacak:**
1. PDLClient — `POST /person/enrich` (email veya name+company ile)
2. pdl_enrich_node — proxycurl ile paralel, score>50 contact'lara
3. Education, skills, previous companies verisi ekle
4. API key yoksa skip

---

## U — Click Tracking Redirect [x]
**Dosyalar:**
- `backend/app/api/routes/tracking.py` (güncelle)

**Ne yapılacak:**
1. `GET /t/c/{sent_email_id}?url=...` → redirect
2. `clicked_at` timestamp set, status → CLICKED
3. URL whitelist / validation (open redirect engelle)
4. Fallback: URL yoksa 404

---

## V — Suppression List Management UI [x]
**Dosyalar:**
- `frontend/src/pages/SuppressionListPage.tsx` (YENİ)
- `backend/app/api/routes/suppression.py` (YENİ)

**Ne yapılacak:**
1. `GET/DELETE /api/suppression` — liste + silme
2. Frontend tablo: email, reason, suppressed_at
3. Manuel ekle / CSV import
4. Kampanya gönderimi öncesi suppression check görünürlüğü

---

## W — Campaign Stats Dashboard [x]
**Dosyalar:**
- `frontend/src/pages/CampaignStatsPage.tsx` (YENİ)
- `backend/app/api/routes/campaigns.py` (stats endpoint güncelle)

**Ne yapılacak:**
1. Open rate, click rate, bounce rate zaman serisi chart
2. A/B variant karşılaştırma bar chart
3. Top performing campaigns tablosu
4. Recharts veya Chart.js

---

## X — IMAP Reply Detection [x]
**Dosyalar:**
- `backend/app/tasks/imap_reply_checker.py` (YENİ)
- `backend/app/models/sent_email.py` (replied_at field)

**Ne yapılacak:**
1. IMAP IDLE veya poll — gelen inbox izle
2. In-Reply-To header match → sent_email.replied_at set
3. Sequence'ı durdur (stop condition)
4. Günlük Celery beat task

---

## Y — Rate Limiting Per Campaign [x]
**Dosyalar:**
- `backend/app/models/campaign.py` (hourly_limit field)
- `backend/app/tasks/campaign_runner.py` (güncelle)

**Ne yapılacak:**
1. Campaign'e `hourly_limit` (varsayılan: 50)
2. Runner: son 1 saatte gönderilen sayıyı hesapla
3. Limit aşıldıysa task'ı `countdown=3600` ile retry
4. Admin UI: campaign edit'e limit field

---

## Z — Test Suite Gaps [x]
**Dosyalar:**
- `backend/tests/tasks/test_campaign_runner.py` (YENİ)
- `backend/tests/tasks/test_daily_report.py` (YENİ)
- `backend/tests/sender/test_compliance.py` (YENİ)

**Ne yapılacak:**
1. campaign_runner: send loop, suppression check, bounce handling
2. daily_report_delivery: open/click rate calc, SMTP send mock
3. compliance: footer injection, unsubscribe link validation
4. Her test dosyası en az 5 test case

---

## Tamamlanan Features
_(tamamlandıkça buraya taşı)_
