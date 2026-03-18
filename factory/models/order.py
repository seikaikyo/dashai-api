from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class SalesOrderBase(SQLModel):
    so_number: str = Field(index=True, max_length=50)
    customer_id: Optional[int] = Field(default=None)
    customer_name: str = Field(default='', max_length=200)
    order_date: str = Field(default='')
    delivery_date: str = Field(default='')
    total_amount: float = Field(default=0)
    currency: str = Field(default='TWD', max_length=10)
    status: str = Field(default='draft', max_length=30)
    payment_terms: str = Field(default='NET30', max_length=50)
    shipping_address: str = Field(default='')
    note: str = Field(default='')


class SalesOrder(SalesOrderBase, table=True):
    __tablename__ = 'sales_orders'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SalesOrderCreate(SalesOrderBase):
    pass


class SalesOrderUpdate(SQLModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    payment_terms: Optional[str] = None
    shipping_address: Optional[str] = None
    note: Optional[str] = None


class SalesOrderLineBase(SQLModel):
    sales_order_id: int
    line_number: int = Field(default=1)
    product_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    quantity: int = Field(default=0)
    unit_price: float = Field(default=0)
    amount: float = Field(default=0)
    delivery_date: str = Field(default='')
    status: str = Field(default='open', max_length=30)


class SalesOrderLine(SalesOrderLineBase, table=True):
    __tablename__ = 'sales_order_lines'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SalesOrderLineCreate(SalesOrderLineBase):
    pass


class SalesOrderLineUpdate(SQLModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    delivery_date: Optional[str] = None
    status: Optional[str] = None


# --- Quotation ---

class QuotationBase(SQLModel):
    quote_number: str = Field(index=True, max_length=50)
    customer_id: Optional[int] = Field(default=None)
    customer_name: str = Field(default='', max_length=200)
    product_name: str = Field(default='', max_length=200)
    quantity: int = Field(default=0)
    unit_price: float = Field(default=0)
    total_amount: float = Field(default=0)
    valid_until: str = Field(default='')
    status: str = Field(default='draft', max_length=30)
    note: str = Field(default='')


class Quotation(QuotationBase, table=True):
    __tablename__ = 'quotations'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QuotationCreate(QuotationBase):
    pass


class QuotationUpdate(SQLModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    valid_until: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- AtpCheck ---

class AtpCheckBase(SQLModel):
    check_number: str = Field(index=True, max_length=50)
    sales_order_id: Optional[int] = Field(default=None)
    product_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    requested_qty: int = Field(default=0)
    available_qty: int = Field(default=0)
    requested_date: str = Field(default='')
    promised_date: str = Field(default='')
    status: str = Field(default='pending', max_length=30)
    note: str = Field(default='')


class AtpCheck(AtpCheckBase, table=True):
    __tablename__ = 'atp_checks'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AtpCheckCreate(AtpCheckBase):
    pass


class AtpCheckUpdate(SQLModel):
    sales_order_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    requested_qty: Optional[int] = None
    available_qty: Optional[int] = None
    requested_date: Optional[str] = None
    promised_date: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- EdiTransaction ---

class EdiTransactionBase(SQLModel):
    transaction_id: str = Field(index=True, max_length=50)
    direction: str = Field(default='inbound', max_length=20)
    doc_type: str = Field(default='', max_length=50)
    partner: str = Field(default='', max_length=200)
    content_summary: str = Field(default='')
    status: str = Field(default='received', max_length=30)
    processed_at: Optional[str] = Field(default=None)
    note: str = Field(default='')


class EdiTransaction(EdiTransactionBase, table=True):
    __tablename__ = 'edi_transactions'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EdiTransactionCreate(EdiTransactionBase):
    pass


class EdiTransactionUpdate(SQLModel):
    direction: Optional[str] = None
    doc_type: Optional[str] = None
    partner: Optional[str] = None
    content_summary: Optional[str] = None
    status: Optional[str] = None
    processed_at: Optional[str] = None
    note: Optional[str] = None


# --- Configuration ---

class ConfigurationBase(SQLModel):
    config_number: str = Field(index=True, max_length=50)
    product_id: Optional[int] = Field(default=None)
    base_product: str = Field(default='', max_length=200)
    options: str = Field(default='')
    bom_output: str = Field(default='')
    price: float = Field(default=0)
    status: str = Field(default='draft', max_length=30)
    note: str = Field(default='')


class Configuration(ConfigurationBase, table=True):
    __tablename__ = 'configurations'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConfigurationCreate(ConfigurationBase):
    pass


class ConfigurationUpdate(SQLModel):
    product_id: Optional[int] = None
    base_product: Optional[str] = None
    options: Optional[str] = None
    bom_output: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- CreditReview ---

class CreditReviewBase(SQLModel):
    review_number: str = Field(index=True, max_length=50)
    customer_id: Optional[int] = Field(default=None)
    customer_name: str = Field(default='', max_length=200)
    credit_score: int = Field(default=0)
    credit_limit: float = Field(default=0)
    current_exposure: float = Field(default=0)
    recommendation: str = Field(default='')
    status: str = Field(default='pending', max_length=30)
    note: str = Field(default='')


class CreditReview(CreditReviewBase, table=True):
    __tablename__ = 'credit_reviews'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CreditReviewCreate(CreditReviewBase):
    pass


class CreditReviewUpdate(SQLModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    credit_score: Optional[int] = None
    credit_limit: Optional[float] = None
    current_exposure: Optional[float] = None
    recommendation: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
