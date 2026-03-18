from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# --- InventoryTransaction ---

class InventoryTransactionBase(SQLModel):
    txn_number: str = Field(index=True, max_length=50)
    material_id: Optional[int] = Field(default=None)
    material_name: str = Field(default='', max_length=200)
    location_code: str = Field(default='', max_length=50)
    txn_type: str = Field(default='receipt', max_length=30)
    quantity: float = Field(default=0)
    reference_type: str = Field(default='', max_length=50)
    reference_id: Optional[int] = Field(default=None)
    operator: str = Field(default='', max_length=100)
    status: str = Field(default='completed', max_length=30)
    note: str = Field(default='')


class InventoryTransaction(InventoryTransactionBase, table=True):
    __tablename__ = 'inventory_transactions'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InventoryTransactionCreate(InventoryTransactionBase):
    pass


class InventoryTransactionUpdate(SQLModel):
    material_id: Optional[int] = None
    material_name: Optional[str] = None
    location_code: Optional[str] = None
    txn_type: Optional[str] = None
    quantity: Optional[float] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    operator: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- AgvTask ---

class AgvTaskBase(SQLModel):
    task_number: str = Field(index=True, max_length=50)
    agv_id: str = Field(default='', max_length=50)
    from_location: str = Field(default='', max_length=50)
    to_location: str = Field(default='', max_length=50)
    material_name: str = Field(default='', max_length=200)
    priority: str = Field(default='normal', max_length=20)
    status: str = Field(default='pending', max_length=30)
    assigned_at: Optional[str] = Field(default=None)
    completed_at: Optional[str] = Field(default=None)
    note: str = Field(default='')


class AgvTask(AgvTaskBase, table=True):
    __tablename__ = 'agv_tasks'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgvTaskCreate(AgvTaskBase):
    pass


class AgvTaskUpdate(SQLModel):
    agv_id: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    material_name: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_at: Optional[str] = None
    completed_at: Optional[str] = None
    note: Optional[str] = None


# --- RfidEvent ---

class RfidEventBase(SQLModel):
    event_id: str = Field(index=True, max_length=50)
    tag_id: str = Field(default='', max_length=100)
    material_name: str = Field(default='', max_length=200)
    reader_location: str = Field(default='', max_length=100)
    event_type: str = Field(default='read', max_length=30)
    timestamp: str = Field(default='', max_length=50)
    status: str = Field(default='normal', max_length=30)
    note: str = Field(default='')


class RfidEvent(RfidEventBase, table=True):
    __tablename__ = 'rfid_events'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RfidEventCreate(RfidEventBase):
    pass


class RfidEventUpdate(SQLModel):
    tag_id: Optional[str] = None
    material_name: Optional[str] = None
    reader_location: Optional[str] = None
    event_type: Optional[str] = None
    timestamp: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- AsrsOperation ---

class AsrsOperationBase(SQLModel):
    operation_number: str = Field(index=True, max_length=50)
    location_code: str = Field(default='', max_length=50)
    material_name: str = Field(default='', max_length=200)
    operation_type: str = Field(default='store', max_length=30)
    quantity: float = Field(default=0)
    crane_id: str = Field(default='', max_length=50)
    status: str = Field(default='pending', max_length=30)
    requested_at: str = Field(default='', max_length=50)
    completed_at: Optional[str] = Field(default=None)
    note: str = Field(default='')


class AsrsOperation(AsrsOperationBase, table=True):
    __tablename__ = 'asrs_operations'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AsrsOperationCreate(AsrsOperationBase):
    pass


class AsrsOperationUpdate(SQLModel):
    location_code: Optional[str] = None
    material_name: Optional[str] = None
    operation_type: Optional[str] = None
    quantity: Optional[float] = None
    crane_id: Optional[str] = None
    status: Optional[str] = None
    requested_at: Optional[str] = None
    completed_at: Optional[str] = None
    note: Optional[str] = None


# --- PtlPick ---

class PtlPickBase(SQLModel):
    pick_number: str = Field(index=True, max_length=50)
    order_id: Optional[int] = Field(default=None)
    zone: str = Field(default='', max_length=50)
    location_code: str = Field(default='', max_length=50)
    material_name: str = Field(default='', max_length=200)
    quantity: int = Field(default=0)
    picked_qty: int = Field(default=0)
    operator: str = Field(default='', max_length=100)
    status: str = Field(default='pending', max_length=30)
    note: str = Field(default='')


class PtlPick(PtlPickBase, table=True):
    __tablename__ = 'ptl_picks'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PtlPickCreate(PtlPickBase):
    pass


class PtlPickUpdate(SQLModel):
    order_id: Optional[int] = None
    zone: Optional[str] = None
    location_code: Optional[str] = None
    material_name: Optional[str] = None
    quantity: Optional[int] = None
    picked_qty: Optional[int] = None
    operator: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- CrossdockOperation ---

class CrossdockOperationBase(SQLModel):
    operation_number: str = Field(index=True, max_length=50)
    inbound_dock: str = Field(default='', max_length=50)
    outbound_dock: str = Field(default='', max_length=50)
    material_name: str = Field(default='', max_length=200)
    quantity: float = Field(default=0)
    destination: str = Field(default='', max_length=100)
    status: str = Field(default='receiving', max_length=30)
    note: str = Field(default='')


class CrossdockOperation(CrossdockOperationBase, table=True):
    __tablename__ = 'crossdock_operations'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CrossdockOperationCreate(CrossdockOperationBase):
    pass


class CrossdockOperationUpdate(SQLModel):
    inbound_dock: Optional[str] = None
    outbound_dock: Optional[str] = None
    material_name: Optional[str] = None
    quantity: Optional[float] = None
    destination: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
