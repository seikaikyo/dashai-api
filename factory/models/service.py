from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# ── ServiceTicket ────────────────────────────────────────────

class ServiceTicketBase(SQLModel):
    ticket_number: str = Field(index=True, max_length=50)
    customer_id: Optional[int] = Field(default=None)
    customer_name: str = Field(default='', max_length=200)
    issue: str = Field(default='')
    priority: str = Field(default='P3', max_length=10)
    sla_hours: int = Field(default=24)
    assigned_to: str = Field(default='', max_length=100)
    status: str = Field(default='open', max_length=30)
    resolved_at: Optional[str] = Field(default=None, max_length=50)
    note: str = Field(default='')


class ServiceTicket(ServiceTicketBase, table=True):
    __tablename__ = 'service_tickets'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceTicketCreate(ServiceTicketBase):
    pass


class ServiceTicketUpdate(SQLModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    issue: Optional[str] = None
    priority: Optional[str] = None
    sla_hours: Optional[int] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    resolved_at: Optional[str] = None
    note: Optional[str] = None


# ── RmaRequest ───────────────────────────────────────────────

class RmaRequestBase(SQLModel):
    rma_number: str = Field(index=True, max_length=50)
    customer_name: str = Field(default='', max_length=200)
    product_name: str = Field(default='', max_length=200)
    reason: str = Field(default='')
    action: str = Field(default='', max_length=100)
    inspection_result: str = Field(default='')
    status: str = Field(default='requested', max_length=30)
    note: str = Field(default='')


class RmaRequest(RmaRequestBase, table=True):
    __tablename__ = 'rma_requests'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RmaRequestCreate(RmaRequestBase):
    pass


class RmaRequestUpdate(SQLModel):
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    reason: Optional[str] = None
    action: Optional[str] = None
    inspection_result: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── FeedbackSurvey ───────────────────────────────────────────

class FeedbackSurveyBase(SQLModel):
    survey_id: str = Field(index=True, max_length=50)
    customer_name: str = Field(default='', max_length=200)
    survey_type: str = Field(default='CSAT', max_length=30)
    score: float = Field(default=0)
    max_score: float = Field(default=5)
    comment: str = Field(default='')
    sentiment: str = Field(default='neutral', max_length=30)
    status: str = Field(default='received', max_length=30)
    note: str = Field(default='')


class FeedbackSurvey(FeedbackSurveyBase, table=True):
    __tablename__ = 'feedback_surveys'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackSurveyCreate(FeedbackSurveyBase):
    pass


class FeedbackSurveyUpdate(SQLModel):
    customer_name: Optional[str] = None
    survey_type: Optional[str] = None
    score: Optional[float] = None
    max_score: Optional[float] = None
    comment: Optional[str] = None
    sentiment: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── FieldOrder ───────────────────────────────────────────────

class FieldOrderBase(SQLModel):
    order_number: str = Field(index=True, max_length=50)
    customer_name: str = Field(default='', max_length=200)
    technician: str = Field(default='', max_length=100)
    issue: str = Field(default='')
    parts_needed: str = Field(default='')
    scheduled_time: str = Field(default='', max_length=50)
    actual_arrival: Optional[str] = Field(default=None, max_length=50)
    status: str = Field(default='scheduled', max_length=30)
    note: str = Field(default='')


class FieldOrder(FieldOrderBase, table=True):
    __tablename__ = 'field_orders'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FieldOrderCreate(FieldOrderBase):
    pass


class FieldOrderUpdate(SQLModel):
    customer_name: Optional[str] = None
    technician: Optional[str] = None
    issue: Optional[str] = None
    parts_needed: Optional[str] = None
    scheduled_time: Optional[str] = None
    actual_arrival: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── KbArticle ────────────────────────────────────────────────

class KbArticleBase(SQLModel):
    article_id: str = Field(index=True, max_length=50)
    title: str = Field(default='', max_length=300)
    category: str = Field(default='', max_length=100)
    content: str = Field(default='')
    views: int = Field(default=0)
    helpful_votes: int = Field(default=0)
    status: str = Field(default='published', max_length=30)
    note: str = Field(default='')


class KbArticle(KbArticleBase, table=True):
    __tablename__ = 'kb_articles'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KbArticleCreate(KbArticleBase):
    pass


class KbArticleUpdate(SQLModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    views: Optional[int] = None
    helpful_votes: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── WarrantyClaim ────────────────────────────────────────────

class WarrantyClaimBase(SQLModel):
    claim_number: str = Field(index=True, max_length=50)
    product_name: str = Field(default='', max_length=200)
    customer_name: str = Field(default='', max_length=200)
    issue: str = Field(default='')
    warranty_type: str = Field(default='standard', max_length=30)
    cost: float = Field(default=0)
    status: str = Field(default='submitted', max_length=30)
    note: str = Field(default='')


class WarrantyClaim(WarrantyClaimBase, table=True):
    __tablename__ = 'warranty_claims'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WarrantyClaimCreate(WarrantyClaimBase):
    pass


class WarrantyClaimUpdate(SQLModel):
    product_name: Optional[str] = None
    customer_name: Optional[str] = None
    issue: Optional[str] = None
    warranty_type: Optional[str] = None
    cost: Optional[float] = None
    status: Optional[str] = None
    note: Optional[str] = None
