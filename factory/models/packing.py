from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# ── PackingOrder ─────────────────────────────────────────────

class PackingOrderBase(SQLModel):
    order_number: str = Field(index=True, max_length=50)
    work_order_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    quantity: int = Field(default=0)
    box_type: str = Field(default='', max_length=50)
    weight_kg: float = Field(default=0)
    operator: str = Field(default='', max_length=100)
    status: str = Field(default='queued', max_length=30)
    note: str = Field(default='')


class PackingOrder(PackingOrderBase, table=True):
    __tablename__ = 'packing_orders'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PackingOrderCreate(PackingOrderBase):
    pass


class PackingOrderUpdate(SQLModel):
    work_order_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    box_type: Optional[str] = None
    weight_kg: Optional[float] = None
    operator: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── LabelJob ────────────────────────────────────────────────

class LabelJobBase(SQLModel):
    job_number: str = Field(index=True, max_length=50)
    label_type: str = Field(default='', max_length=50)
    content: str = Field(default='')
    printer: str = Field(default='', max_length=100)
    quantity: int = Field(default=1)
    status: str = Field(default='pending', max_length=30)
    note: str = Field(default='')


class LabelJob(LabelJobBase, table=True):
    __tablename__ = 'label_jobs'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LabelJobCreate(LabelJobBase):
    pass


class LabelJobUpdate(SQLModel):
    label_type: Optional[str] = None
    content: Optional[str] = None
    printer: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── PalletRecord ─────────────────────────────────────────────

class PalletRecordBase(SQLModel):
    pallet_number: str = Field(index=True, max_length=50)
    sscc: str = Field(default='', max_length=50)
    box_count: int = Field(default=0)
    total_weight_kg: float = Field(default=0)
    wrap_status: str = Field(default='pending', max_length=30)
    destination: str = Field(default='', max_length=200)
    status: str = Field(default='open', max_length=30)
    note: str = Field(default='')


class PalletRecord(PalletRecordBase, table=True):
    __tablename__ = 'pallet_records'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PalletRecordCreate(PalletRecordBase):
    pass


class PalletRecordUpdate(SQLModel):
    sscc: Optional[str] = None
    box_count: Optional[int] = None
    total_weight_kg: Optional[float] = None
    wrap_status: Optional[str] = None
    destination: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── SerialNumber ─────────────────────────────────────────────

class SerialNumberBase(SQLModel):
    serial: str = Field(index=True, max_length=100)
    product_name: str = Field(default='', max_length=200)
    level: str = Field(default='unit', max_length=30)
    parent_serial: Optional[str] = Field(default=None, max_length=100)
    packing_order_id: Optional[int] = Field(default=None)
    status: str = Field(default='active', max_length=30)
    note: str = Field(default='')


class SerialNumber(SerialNumberBase, table=True):
    __tablename__ = 'serial_numbers'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SerialNumberCreate(SerialNumberBase):
    pass


class SerialNumberUpdate(SQLModel):
    product_name: Optional[str] = None
    level: Optional[str] = None
    parent_serial: Optional[str] = None
    packing_order_id: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── WeightCheck ──────────────────────────────────────────────

class WeightCheckBase(SQLModel):
    check_number: str = Field(index=True, max_length=50)
    product_name: str = Field(default='', max_length=200)
    expected_weight_g: float = Field(default=0)
    actual_weight_g: float = Field(default=0)
    tolerance_pct: float = Field(default=2.0)
    result: str = Field(default='pass', max_length=20)
    line: str = Field(default='', max_length=50)
    timestamp: str = Field(default='', max_length=50)
    note: str = Field(default='')


class WeightCheck(WeightCheckBase, table=True):
    __tablename__ = 'weight_checks'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WeightCheckCreate(WeightCheckBase):
    pass


class WeightCheckUpdate(SQLModel):
    product_name: Optional[str] = None
    expected_weight_g: Optional[float] = None
    actual_weight_g: Optional[float] = None
    tolerance_pct: Optional[float] = None
    result: Optional[str] = None
    line: Optional[str] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None


# ── TraceEvent ───────────────────────────────────────────────

class TraceEventBase(SQLModel):
    event_id: str = Field(index=True, max_length=50)
    serial: str = Field(default='', max_length=100)
    event_type: str = Field(default='pack', max_length=30)
    location: str = Field(default='', max_length=200)
    timestamp: str = Field(default='', max_length=50)
    operator: str = Field(default='', max_length=100)
    note: str = Field(default='')


class TraceEvent(TraceEventBase, table=True):
    __tablename__ = 'trace_events'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TraceEventCreate(TraceEventBase):
    pass


class TraceEventUpdate(SQLModel):
    serial: Optional[str] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    timestamp: Optional[str] = None
    operator: Optional[str] = None
    note: Optional[str] = None
