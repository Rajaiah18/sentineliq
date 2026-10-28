"""
SentinelIQ Domain Entities
Consistent Pydantic models for all entities:
Customer, Account, Merchant, Device, Transaction, TransferLink,
RiskRule, Alert, Case, AnalystAction, AuditEvent, User, GroundTruth
"""
from typing import Optional, List, Dict, Any
from pydantic import Field
from backend.app.models.base import SentinelBaseModel


class Customer(SentinelBaseModel):
    customer_id: str = Field(..., description="Stable identifier, e.g. CUS-000001")
    first_name: str
    last_name: str
    date_of_birth: str = Field(..., description="YYYY-MM-DD")
    customer_type: str = Field(..., description="INDIVIDUAL | BUSINESS")
    risk_profile: str = Field(..., description="LOW | MEDIUM | HIGH")
    country_code: str = Field(..., description="ISO 2-letter country code")
    customer_status: str = Field(..., description="ACTIVE | SUSPENDED | CLOSED")
    created_at: str
    updated_at: str


class Account(SentinelBaseModel):
    account_id: str = Field(..., description="Stable identifier, e.g. ACC-CUS-000001-01")
    customer_id: str = Field(..., description="Reference to Customer")
    account_type: str = Field(..., description="CHECKING | SAVINGS | BUSINESS | INVESTMENT")
    currency: str = Field(..., description="Currency code, e.g. USD, EUR, GBP")
    opening_balance: float = Field(..., ge=0.0)
    current_balance: float
    overdraft_limit: float = Field(0.0, ge=0.0)
    account_status: str = Field(..., description="OPEN | RESTRICTED | CLOSED")
    opened_at: str
    closed_at: Optional[str] = None
    created_at: str
    updated_at: str


class Merchant(SentinelBaseModel):
    merchant_id: str = Field(..., description="Stable identifier, e.g. MER-00001")
    merchant_name: str
    merchant_category: str = Field(..., description="RETAIL | TRAVEL | GAMBLING | CRYPTO | ELECTRONICS | DINING | SERVICES")
    merchant_country: str = Field(..., description="ISO 2-letter country code")
    merchant_risk_level: str = Field(..., description="LOW | MEDIUM | HIGH")
    created_at: str


class Device(SentinelBaseModel):
    device_id: str = Field(..., description="Stable identifier, e.g. DEV-000001")
    device_fingerprint: str = Field(..., description="Deterministic synthetic SHA-256 fingerprint")
    device_type: str = Field(..., description="MOBILE | DESKTOP | TABLET")
    operating_system: str = Field(..., description="IOS | ANDROID | WINDOWS | MACOS | LINUX")
    ip_country: str = Field(..., description="ISO 2-letter country code")
    first_seen_at: str
    device_status: str = Field(..., description="TRUSTED | UNTRUSTED | FLAGGED")


class Transaction(SentinelBaseModel):
    transaction_id: str = Field(..., description="Stable identifier, e.g. TXN-2026-00000001")
    source_account_id: str = Field(..., description="Source account identifier")
    destination_account_id: Optional[str] = Field(None, description="Destination account if transfer/internal")
    customer_id: str = Field(..., description="Customer initiating or owning source account")
    merchant_id: Optional[str] = Field(None, description="Merchant for card/pos/purchase transactions")
    device_id: Optional[str] = Field(None, description="Device used for channel execution")
    transaction_type: str = Field(..., description="CARD_PAYMENT | PURCHASE | CASH_WITHDRAWAL | DEPOSIT | ACCOUNT_TRANSFER | BANK_TRANSFER | REFUND")
    amount: float = Field(..., gt=0.0)
    currency: str
    transaction_status: str = Field(..., description="COMPLETED | PENDING | FAILED | REVERSED")
    transaction_timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    channel: str = Field(..., description="MOBILE_APP | WEB_PORTAL | ATM | POS | BRANCH")
    reference_id: str = Field(..., description="External/wire reference identifier")
    transfer_group_id: Optional[str] = Field(None, description="Links reciprocal legs of transfer")
    balance_before: Optional[float] = None
    balance_after: Optional[float] = None
    created_at: str


class TransferLink(SentinelBaseModel):
    transfer_link_id: str = Field(..., description="Stable identifier, e.g. TRL-2026-00000001")
    transfer_group_id: str = Field(..., description="Links source and destination transfer legs")
    source_transaction_id: str
    destination_transaction_id: str
    source_account_id: str
    destination_account_id: str
    amount: float = Field(..., gt=0.0)
    currency: str
    created_at: str


class RiskRule(SentinelBaseModel):
    rule_id: str = Field(..., description="e.g. RULE-HIGH-VALUE")
    rule_name: str
    description: str
    rule_category: str = Field(..., description="INTEGRITY | COMPLIANCE | VELOCITY | BEHAVIORAL | VALUE")
    enabled: bool = True
    severity: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    weight: float = Field(..., ge=0.0, le=100.0)
    threshold: float
    configuration: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"
    created_at: str
    updated_at: str


class Alert(SentinelBaseModel):
    alert_id: str = Field(..., description="Stable identifier, e.g. ALT-2026-000001")
    alert_type: str = Field(..., description="SUSPICIOUS_ACTIVITY | DATA_INTEGRITY")
    title: str
    description: str
    severity: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    risk_score: float = Field(..., ge=0.0, le=100.0)
    alert_status: str = Field(..., description="NEW | UNDER_REVIEW | ESCALATED | CLOSED")
    triggered_transaction_ids: List[str] = Field(default_factory=list, description="IDs of triggering transactions")
    customer_id: str
    account_ids: List[str] = Field(default_factory=list)
    triggered_rule_ids: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    explanation: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class Case(SentinelBaseModel):
    case_id: str = Field(..., description="Stable identifier, e.g. CASE-2026-000001")
    case_title: str
    description: str
    case_status: str = Field(..., description="OPEN | IN_PROGRESS | PENDING_REVIEW | CLOSED")
    priority: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    alert_ids: List[str] = Field(default_factory=list)
    customer_id: str
    assigned_analyst_id: Optional[str] = None
    disposition: Optional[str] = Field(None, description="CONFIRMED_SUSPICIOUS | FALSE_POSITIVE | INCONCLUSIVE | ESCALATED")
    disposition_reason: Optional[str] = None
    created_at: str
    updated_at: str
    closed_at: Optional[str] = None


class AnalystAction(SentinelBaseModel):
    action_id: str = Field(..., description="Stable identifier, e.g. ACT-2026-000001")
    case_id: str
    alert_id: Optional[str] = None
    analyst_id: str
    action_type: str = Field(..., description="ASSIGNED | STATUS_CHANGE | NOTE_ADDED | DISPOSITION_RECORDED | ESCALATED")
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    disposition: Optional[str] = None
    comment: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditEvent(SentinelBaseModel):
    event_id: str = Field(..., description="Stable identifier, e.g. AUD-2026-00000001")
    event_type: str
    actor_id: str
    entity_type: str
    entity_id: str
    timestamp: str
    action_summary: str
    previous_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


class User(SentinelBaseModel):
    user_id: str
    username: str
    email: str
    hashed_password: str
    role: str = Field(..., description="ADMIN | ANALYST | COMPLIANCE_REVIEWER | READ_ONLY")
    full_name: str
    is_active: bool = True
    created_at: str


class GroundTruth(SentinelBaseModel):
    ground_truth_id: str = Field(..., description="Stable identifier, e.g. GT-2026-00000001")
    entity_type: str = Field(..., description="TRANSACTION | TRANSFER | ALERT | CASE")
    entity_id: str
    is_suspicious: bool
    scenario_id: str
    expected_rule_id: Optional[str] = None
    scenario_category: str
    expected_outcome: str
    notes: str
