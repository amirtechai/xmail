"""SQLAlchemy ORM models — all imports trigger mapper registration."""

from app.database import Base
from app.models.agent_memory import AgentMemory
from app.models.agent_run import AgentRun, RunStatus, RunType
from app.models.audit_log import AuditLog
from app.models.bot_state import BotState, BotStateEnum
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_sequence import CampaignSequence
from app.models.campaign_sequence_step import CampaignSequenceStep
from app.models.daily_report import DailyReport
from app.models.discovered_contact import DiscoveredContact, VerifiedStatus
from app.models.llm_config import LLMConfiguration, LLMProvider
from app.models.scraping_source import ScrapingSource, SourceType
from app.models.sent_email import SentEmail, SentEmailStatus
from app.models.smtp_config import SMTPConfiguration
from app.models.suggestion_history import SuggestionHistory
from app.models.suppression_list import SuppressionList, SuppressionReason
from app.models.target_audience_type import AudienceCategory, TargetAudienceType
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "CampaignSequence",
    "CampaignSequenceStep",
    "User",
    "UserRole",
    "LLMConfiguration",
    "LLMProvider",
    "SMTPConfiguration",
    "TargetAudienceType",
    "AudienceCategory",
    "Campaign",
    "CampaignStatus",
    "DiscoveredContact",
    "VerifiedStatus",
    "SuggestionHistory",
    "SuppressionList",
    "SuppressionReason",
    "SentEmail",
    "SentEmailStatus",
    "AgentRun",
    "RunType",
    "RunStatus",
    "AgentMemory",
    "AuditLog",
    "DailyReport",
    "ScrapingSource",
    "SourceType",
    "BotState",
    "BotStateEnum",
]
