from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# ── Shipment ─────────────────────────────────────────────────

class ShipmentBase(SQLModel):
    shipment_number: str = Field(index=True, max_length=50)
    sales_order_id: Optional[int] = Field(default=None)
    destination: str = Field(default='', max_length=200)
    carrier: str = Field(default='', max_length=100)
    eta: str = Field(default='', max_length=50)
    cost: float = Field(default=0)
    weight_kg: float = Field(default=0)
    status: str = Field(default='pending', max_length=30)
    note: str = Field(default='')


class Shipment(ShipmentBase, table=True):
    __tablename__ = 'shipments'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentUpdate(SQLModel):
    sales_order_id: Optional[int] = None
    destination: Optional[str] = None
    carrier: Optional[str] = None
    eta: Optional[str] = None
    cost: Optional[float] = None
    weight_kg: Optional[float] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── DockSchedule ─────────────────────────────────────────────

class DockScheduleBase(SQLModel):
    schedule_number: str = Field(index=True, max_length=50)
    dock_door: str = Field(default='', max_length=50)
    carrier: str = Field(default='', max_length=100)
    vehicle_plate: str = Field(default='', max_length=50)
    scheduled_time: str = Field(default='', max_length=50)
    actual_arrival: Optional[str] = Field(default=None, max_length=50)
    load_type: str = Field(default='outbound', max_length=30)
    status: str = Field(default='scheduled', max_length=30)
    note: str = Field(default='')


class DockSchedule(DockScheduleBase, table=True):
    __tablename__ = 'dock_schedules'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DockScheduleCreate(DockScheduleBase):
    pass


class DockScheduleUpdate(SQLModel):
    dock_door: Optional[str] = None
    carrier: Optional[str] = None
    vehicle_plate: Optional[str] = None
    scheduled_time: Optional[str] = None
    actual_arrival: Optional[str] = None
    load_type: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── TrackingEvent ────────────────────────────────────────────

class TrackingEventBase(SQLModel):
    event_id: str = Field(index=True, max_length=50)
    shipment_id: Optional[int] = Field(default=None)
    location: str = Field(default='', max_length=200)
    milestone: str = Field(default='', max_length=100)
    eta: str = Field(default='', max_length=50)
    status: str = Field(default='in_transit', max_length=30)
    timestamp: str = Field(default='', max_length=50)
    note: str = Field(default='')


class TrackingEvent(TrackingEventBase, table=True):
    __tablename__ = 'tracking_events'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TrackingEventCreate(TrackingEventBase):
    pass


class TrackingEventUpdate(SQLModel):
    shipment_id: Optional[int] = None
    location: Optional[str] = None
    milestone: Optional[str] = None
    eta: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None


# ── CustomsDeclaration ───────────────────────────────────────

class CustomsDeclarationBase(SQLModel):
    declaration_number: str = Field(index=True, max_length=50)
    shipment_id: Optional[int] = Field(default=None)
    destination_country: str = Field(default='', max_length=100)
    hs_code: str = Field(default='', max_length=50)
    duty_pct: float = Field(default=0)
    doc_count: int = Field(default=0)
    status: str = Field(default='preparing', max_length=30)
    note: str = Field(default='')


class CustomsDeclaration(CustomsDeclarationBase, table=True):
    __tablename__ = 'customs_declarations'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CustomsDeclarationCreate(CustomsDeclarationBase):
    pass


class CustomsDeclarationUpdate(SQLModel):
    shipment_id: Optional[int] = None
    destination_country: Optional[str] = None
    hs_code: Optional[str] = None
    duty_pct: Optional[float] = None
    doc_count: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── CarrierRate ──────────────────────────────────────────────

class CarrierRateBase(SQLModel):
    rate_id: str = Field(index=True, max_length=50)
    carrier: str = Field(default='', max_length=100)
    service_type: str = Field(default='', max_length=50)
    rate_per_kg: float = Field(default=0)
    sla_pct: float = Field(default=0)
    volume_monthly: int = Field(default=0)
    score: float = Field(default=0)
    status: str = Field(default='active', max_length=30)
    note: str = Field(default='')


class CarrierRate(CarrierRateBase, table=True):
    __tablename__ = 'carrier_rates'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CarrierRateCreate(CarrierRateBase):
    pass


class CarrierRateUpdate(SQLModel):
    carrier: Optional[str] = None
    service_type: Optional[str] = None
    rate_per_kg: Optional[float] = None
    sla_pct: Optional[float] = None
    volume_monthly: Optional[int] = None
    score: Optional[float] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ── DeliveryProof ────────────────────────────────────────────

class DeliveryProofBase(SQLModel):
    proof_number: str = Field(index=True, max_length=50)
    shipment_id: Optional[int] = Field(default=None)
    receiver_name: str = Field(default='', max_length=100)
    signature: str = Field(default='')
    photo_url: str = Field(default='', max_length=500)
    delivered_at: str = Field(default='', max_length=50)
    status: str = Field(default='pending', max_length=30)
    note: str = Field(default='')


class DeliveryProof(DeliveryProofBase, table=True):
    __tablename__ = 'delivery_proofs'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DeliveryProofCreate(DeliveryProofBase):
    pass


class DeliveryProofUpdate(SQLModel):
    shipment_id: Optional[int] = None
    receiver_name: Optional[str] = None
    signature: Optional[str] = None
    photo_url: Optional[str] = None
    delivered_at: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
