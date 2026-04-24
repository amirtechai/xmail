"""Seed 60 target audience types into the database.

Run: python scripts/seed_audience_types.py
Idempotent: checks existing keys before inserting.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.target_audience_type import AudienceCategory, TargetAudienceType

# fmt: off
AUDIENCE_TYPES: list[dict] = [

    # ── MARKETS (10) ──────────────────────────────────────────────────────────
    {
        "key": "forex_broker",
        "label_en": "Forex Broker",
        "label_tr": "Forex Brokeri",
        "category": AudienceCategory.MARKETS,
        "description": "Retail and institutional forex trading brokers",
        "icon_name": "currency-exchange",
    },
    {
        "key": "crypto_exchange",
        "label_en": "Crypto Exchange",
        "label_tr": "Kripto Borsası",
        "category": AudienceCategory.MARKETS,
        "description": "Centralized and decentralized cryptocurrency exchanges",
        "icon_name": "bitcoin",
    },
    {
        "key": "stock_broker",
        "label_en": "Stock Broker",
        "label_tr": "Hisse Senedi Brokeri",
        "category": AudienceCategory.MARKETS,
        "description": "Equity trading brokerage firms and platforms",
        "icon_name": "chart-line",
    },
    {
        "key": "commodities_broker",
        "label_en": "Commodities Broker",
        "label_tr": "Emtia Brokeri",
        "category": AudienceCategory.MARKETS,
        "description": "Futures and commodities trading brokers",
        "icon_name": "oil-barrel",
    },
    {
        "key": "cfd_provider",
        "label_en": "CFD Provider",
        "label_tr": "CFD Sağlayıcısı",
        "category": AudienceCategory.MARKETS,
        "description": "Contracts for Difference trading platforms",
        "icon_name": "trending-up",
    },
    {
        "key": "options_broker",
        "label_en": "Options Broker",
        "label_tr": "Opsiyon Brokeri",
        "category": AudienceCategory.MARKETS,
        "description": "Options and derivatives brokerage platforms",
        "icon_name": "layers",
    },
    {
        "key": "multi_asset_broker",
        "label_en": "Multi-Asset Broker",
        "label_tr": "Çok Varlıklı Broker",
        "category": AudienceCategory.MARKETS,
        "description": "Brokers offering stocks, crypto, forex in one platform",
        "icon_name": "briefcase",
    },
    {
        "key": "defi_protocol",
        "label_en": "DeFi Protocol",
        "label_tr": "DeFi Protokolü",
        "category": AudienceCategory.MARKETS,
        "description": "Decentralized finance lending, DEX, and yield protocols",
        "icon_name": "link",
    },
    {
        "key": "nft_marketplace",
        "label_en": "NFT Marketplace",
        "label_tr": "NFT Pazaryeri",
        "category": AudienceCategory.MARKETS,
        "description": "Platforms for minting and trading non-fungible tokens",
        "icon_name": "image",
    },
    {
        "key": "prop_trading_firm",
        "label_en": "Prop Trading Firm",
        "label_tr": "Proprietary Trading Firması",
        "category": AudienceCategory.MARKETS,
        "description": "Proprietary trading firms and funded trader programs",
        "icon_name": "zap",
    },

    # ── NEWS & MEDIA (10) ─────────────────────────────────────────────────────
    {
        "key": "financial_news_outlet",
        "label_en": "Financial News Outlet",
        "label_tr": "Finansal Haber Sitesi",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Print and digital financial news publishers",
        "icon_name": "newspaper",
    },
    {
        "key": "investment_newsletter",
        "label_en": "Investment Newsletter",
        "label_tr": "Yatırım Bülteni",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Paid and free investment research newsletters",
        "icon_name": "mail",
    },
    {
        "key": "finance_podcast",
        "label_en": "Finance Podcast",
        "label_tr": "Finans Podcast'i",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Finance, trading, and investing podcast shows",
        "icon_name": "mic",
    },
    {
        "key": "youtube_finance",
        "label_en": "YouTube Finance Channel",
        "label_tr": "YouTube Finans Kanalı",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Finance education and trading review YouTube channels",
        "icon_name": "play-circle",
    },
    {
        "key": "fintech_blog",
        "label_en": "Fintech Blog",
        "label_tr": "Fintech Blog",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Independent fintech and trading strategy blogs",
        "icon_name": "edit",
    },
    {
        "key": "financial_data_provider",
        "label_en": "Financial Data Provider",
        "label_tr": "Finansal Veri Sağlayıcısı",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Market data, analytics, and research data firms",
        "icon_name": "database",
    },
    {
        "key": "crypto_media",
        "label_en": "Crypto Media",
        "label_tr": "Kripto Medyası",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Crypto-focused news sites and research publications",
        "icon_name": "rss",
    },
    {
        "key": "trade_publication",
        "label_en": "Trade Publication",
        "label_tr": "Sektör Yayını",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "B2B trade magazines and industry journals",
        "icon_name": "book-open",
    },
    {
        "key": "price_comparison_media",
        "label_en": "Price Comparison / Review Site",
        "label_tr": "Fiyat Karşılaştırma Sitesi",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Broker comparison and product review platforms",
        "icon_name": "search",
    },
    {
        "key": "substack_writer",
        "label_en": "Substack / Paid Newsletter Writer",
        "label_tr": "Substack Yazarı",
        "category": AudienceCategory.NEWS_MEDIA,
        "description": "Paid newsletter authors on Substack, Beehiiv, Ghost",
        "icon_name": "pen-tool",
    },

    # ── ANALYSIS (6) ──────────────────────────────────────────────────────────
    {
        "key": "forex_signal_provider",
        "label_en": "Forex Signal Provider",
        "label_tr": "Forex Sinyal Sağlayıcısı",
        "category": AudienceCategory.ANALYSIS,
        "description": "Companies and individuals selling forex trading signals",
        "icon_name": "radio",
    },
    {
        "key": "quant_research_firm",
        "label_en": "Quant Research Firm",
        "label_tr": "Kantitatif Araştırma Firması",
        "category": AudienceCategory.ANALYSIS,
        "description": "Quantitative finance research and strategy firms",
        "icon_name": "cpu",
    },
    {
        "key": "market_research_firm",
        "label_en": "Market Research Firm",
        "label_tr": "Pazar Araştırma Firması",
        "category": AudienceCategory.ANALYSIS,
        "description": "B2B market research and consumer insights firms",
        "icon_name": "bar-chart-2",
    },
    {
        "key": "trading_analytics_saas",
        "label_en": "Trading Analytics SaaS",
        "label_tr": "Trading Analitik SaaS",
        "category": AudienceCategory.ANALYSIS,
        "description": "Software platforms for trade analysis and back-testing",
        "icon_name": "activity",
    },
    {
        "key": "risk_analytics_vendor",
        "label_en": "Risk Analytics Vendor",
        "label_tr": "Risk Analitik Sağlayıcısı",
        "category": AudienceCategory.ANALYSIS,
        "description": "Enterprise risk measurement and modeling software",
        "icon_name": "shield",
    },
    {
        "key": "esg_research",
        "label_en": "ESG Research Provider",
        "label_tr": "ESG Araştırma Sağlayıcısı",
        "category": AudienceCategory.ANALYSIS,
        "description": "Environmental, Social, Governance data and scoring firms",
        "icon_name": "leaf",
    },

    # ── INFLUENCERS (7) ───────────────────────────────────────────────────────
    {
        "key": "fintech_influencer",
        "label_en": "Fintech Influencer",
        "label_tr": "Fintech Influencer",
        "category": AudienceCategory.INFLUENCERS,
        "description": "High-follower fintech and trading content creators",
        "icon_name": "star",
    },
    {
        "key": "crypto_influencer",
        "label_en": "Crypto Influencer",
        "label_tr": "Kripto Influencer",
        "category": AudienceCategory.INFLUENCERS,
        "description": "Twitter/X and YouTube crypto opinion leaders",
        "icon_name": "twitter",
    },
    {
        "key": "linkedin_finance_creator",
        "label_en": "LinkedIn Finance Creator",
        "label_tr": "LinkedIn Finans İçerik Üreticisi",
        "category": AudienceCategory.INFLUENCERS,
        "description": "Finance and investing content creators on LinkedIn",
        "icon_name": "linkedin",
    },
    {
        "key": "tiktok_trader",
        "label_en": "TikTok Trader / FinTok",
        "label_tr": "TikTok Trader / FinTok",
        "category": AudienceCategory.INFLUENCERS,
        "description": "Short-form finance content creators on TikTok and Reels",
        "icon_name": "video",
    },
    {
        "key": "forex_affiliate",
        "label_en": "Forex Affiliate",
        "label_tr": "Forex Affiliate",
        "category": AudienceCategory.INFLUENCERS,
        "description": "Affiliate marketers promoting forex and CFD brokers",
        "icon_name": "share-2",
    },
    {
        "key": "community_manager_finance",
        "label_en": "Finance Community Manager",
        "label_tr": "Finans Topluluk Yöneticisi",
        "category": AudienceCategory.INFLUENCERS,
        "description": "Discord, Telegram, and Reddit finance community leaders",
        "icon_name": "users",
    },
    {
        "key": "conference_speaker",
        "label_en": "Finance Conference Speaker",
        "label_tr": "Finans Konferans Konuşmacısı",
        "category": AudienceCategory.INFLUENCERS,
        "description": "Keynote speakers at iFX EXPO, Money2020, Finovate",
        "icon_name": "mic-2",
    },

    # ── EDUCATION (5) ─────────────────────────────────────────────────────────
    {
        "key": "trading_academy",
        "label_en": "Trading Academy",
        "label_tr": "Trading Akademisi",
        "category": AudienceCategory.EDUCATION,
        "description": "Online and offline trading education academies",
        "icon_name": "graduation-cap",
    },
    {
        "key": "forex_course_creator",
        "label_en": "Forex Course Creator",
        "label_tr": "Forex Kurs Oluşturucusu",
        "category": AudienceCategory.EDUCATION,
        "description": "Udemy, Skillshare, and independent course creators",
        "icon_name": "book",
    },
    {
        "key": "university_finance_dept",
        "label_en": "University Finance Department",
        "label_tr": "Üniversite Finans Bölümü",
        "category": AudienceCategory.EDUCATION,
        "description": "Finance, economics, and business school departments",
        "icon_name": "building",
    },
    {
        "key": "cfa_cpa_prep",
        "label_en": "CFA / CPA Prep Provider",
        "label_tr": "CFA / CPA Hazırlık Sağlayıcısı",
        "category": AudienceCategory.EDUCATION,
        "description": "Professional certification exam preparation providers",
        "icon_name": "award",
    },
    {
        "key": "bootcamp_fintech",
        "label_en": "Fintech Bootcamp",
        "label_tr": "Fintech Bootcamp",
        "category": AudienceCategory.EDUCATION,
        "description": "Intensive fintech and blockchain developer bootcamps",
        "icon_name": "code",
    },

    # ── BROKERS & INSTITUTIONS (9) ────────────────────────────────────────────
    {
        "key": "introducing_broker",
        "label_en": "Introducing Broker",
        "label_tr": "Introducing Broker",
        "category": AudienceCategory.BROKERS,
        "description": "IBs and white-label broker operators",
        "icon_name": "handshake",
    },
    {
        "key": "prime_broker",
        "label_en": "Prime Broker",
        "label_tr": "Prime Broker",
        "category": AudienceCategory.BROKERS,
        "description": "Prime brokerage services for hedge funds and institutions",
        "icon_name": "landmark",
    },
    {
        "key": "financial_advisor_ria",
        "label_en": "Financial Advisor / RIA",
        "label_tr": "Finansal Danışman / RIA",
        "category": AudienceCategory.BROKERS,
        "description": "Registered investment advisors and wealth managers",
        "icon_name": "user-check",
    },
    {
        "key": "hedge_fund",
        "label_en": "Hedge Fund",
        "label_tr": "Hedge Fon",
        "category": AudienceCategory.BROKERS,
        "description": "Quantitative and discretionary hedge funds",
        "icon_name": "shield-off",
    },
    {
        "key": "private_equity",
        "label_en": "Private Equity Firm",
        "label_tr": "Özel Sermaye Şirketi",
        "category": AudienceCategory.BROKERS,
        "description": "PE funds and portfolio operations teams",
        "icon_name": "dollar-sign",
    },
    {
        "key": "family_office",
        "label_en": "Family Office",
        "label_tr": "Aile Ofisi",
        "category": AudienceCategory.BROKERS,
        "description": "Single and multi-family wealth management offices",
        "icon_name": "home",
    },
    {
        "key": "crypto_fund_vc",
        "label_en": "Crypto Fund / Web3 VC",
        "label_tr": "Kripto Fon / Web3 VC",
        "category": AudienceCategory.BROKERS,
        "description": "Crypto-focused venture capital and investment funds",
        "icon_name": "trending-up",
    },
    {
        "key": "asset_management_firm",
        "label_en": "Asset Management Firm",
        "label_tr": "Varlık Yönetim Şirketi",
        "category": AudienceCategory.BROKERS,
        "description": "Mutual funds, ETF issuers, and institutional asset managers",
        "icon_name": "pie-chart",
    },
    {
        "key": "corporate_treasury",
        "label_en": "Corporate Treasury",
        "label_tr": "Kurumsal Hazine",
        "category": AudienceCategory.BROKERS,
        "description": "Corporate treasury and FX risk management teams",
        "icon_name": "briefcase",
    },

    # ── TOOLS & PLATFORMS (5) ─────────────────────────────────────────────────
    {
        "key": "fx_tech_vendor",
        "label_en": "FX Technology Vendor",
        "label_tr": "FX Teknoloji Sağlayıcısı",
        "category": AudienceCategory.TOOLS,
        "description": "Trading platform, bridge, and LP connectivity vendors",
        "icon_name": "settings",
    },
    {
        "key": "payment_processor",
        "label_en": "Payment Processor",
        "label_tr": "Ödeme İşlemcisi",
        "category": AudienceCategory.TOOLS,
        "description": "Online and POS payment processing companies",
        "icon_name": "credit-card",
    },
    {
        "key": "kyc_aml_vendor",
        "label_en": "KYC / AML Vendor",
        "label_tr": "KYC / AML Sağlayıcısı",
        "category": AudienceCategory.TOOLS,
        "description": "Identity verification and anti-money-laundering tech",
        "icon_name": "fingerprint",
    },
    {
        "key": "regtech_firm",
        "label_en": "Regtech Firm",
        "label_tr": "Regtech Firması",
        "category": AudienceCategory.TOOLS,
        "description": "Regulatory compliance technology providers",
        "icon_name": "check-square",
    },
    {
        "key": "wealthtech_platform",
        "label_en": "Wealthtech Platform",
        "label_tr": "Wealthtech Platformu",
        "category": AudienceCategory.TOOLS,
        "description": "Robo-advisors, portfolio rebalancing, and digital wealth",
        "icon_name": "sliders",
    },

    # ── OTHER (8) ─────────────────────────────────────────────────────────────
    {
        "key": "ecommerce_marketplace",
        "label_en": "eCommerce Marketplace",
        "label_tr": "eCommerce Pazaryeri",
        "category": AudienceCategory.OTHER,
        "description": "Multi-vendor online marketplaces (global expansion targets)",
        "icon_name": "shopping-cart",
    },
    {
        "key": "d2c_brand",
        "label_en": "D2C Brand",
        "label_tr": "D2C Marka",
        "category": AudienceCategory.OTHER,
        "description": "Direct-to-consumer product brands selling online",
        "icon_name": "package",
    },
    {
        "key": "b2b_saas_startup",
        "label_en": "B2B SaaS Startup",
        "label_tr": "B2B SaaS Startup",
        "category": AudienceCategory.OTHER,
        "description": "Early-stage B2B software-as-a-service companies",
        "icon_name": "cloud",
    },
    {
        "key": "neobank",
        "label_en": "Neobank",
        "label_tr": "Neobank",
        "category": AudienceCategory.OTHER,
        "description": "Digital-only banking platforms and challengers",
        "icon_name": "smartphone",
    },
    {
        "key": "insurtech",
        "label_en": "Insurtech Company",
        "label_tr": "Insurtech Şirketi",
        "category": AudienceCategory.OTHER,
        "description": "Digital insurance platforms and MGA startups",
        "icon_name": "umbrella",
    },
    {
        "key": "trade_association",
        "label_en": "Trade Association",
        "label_tr": "Ticaret Derneği",
        "category": AudienceCategory.OTHER,
        "description": "Financial industry trade bodies and chambers of commerce",
        "icon_name": "globe",
    },
    {
        "key": "global_expansion_sea",
        "label_en": "SEA Market Partner",
        "label_tr": "Güneydoğu Asya Pazar Ortağı",
        "category": AudienceCategory.OTHER,
        "description": "Businesses targeting Southeast Asia market expansion",
        "icon_name": "map-pin",
    },
    {
        "key": "global_expansion_mena",
        "label_en": "MENA Market Partner",
        "label_tr": "MENA Pazar Ortağı",
        "category": AudienceCategory.OTHER,
        "description": "Middle East and North Africa market operators",
        "icon_name": "map-pin",
    },
]
# fmt: on

assert len(AUDIENCE_TYPES) == 60, f"Expected 60, got {len(AUDIENCE_TYPES)}"


async def seed(session: AsyncSession) -> None:
    existing = (await session.execute(select(TargetAudienceType))).scalars().all()
    existing_keys = {t.key for t in existing}

    new_types = [
        TargetAudienceType(
            key=row["key"],
            label_en=row["label_en"],
            label_tr=row["label_tr"],
            description=row["description"],
            category=row["category"].value,
            icon_name=row.get("icon_name", "briefcase"),
            is_enabled_default=True,
        )
        for row in AUDIENCE_TYPES
        if row["key"] not in existing_keys
    ]

    if new_types:
        session.add_all(new_types)
        await session.commit()
        print(f"Seeded {len(new_types)} audience types.")
    else:
        print("All audience types already exist — skipping.")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
