from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# --- SupplierEvaluation ---

class SupplierEvaluationBase(SQLModel):
    eval_number: str = Field(index=True, max_length=50)
    supplier_id: Optional[int] = Field(default=None)
    supplier_name: str = Field(default='', max_length=200)
    period: str = Field(default='', max_length=30)
    otd_score: float = Field(default=0)
    quality_score: float = Field(default=0)
    cost_score: float = Field(default=0)
    overall_rating: str = Field(default='B', max_length=10)
    status: str = Field(default='draft', max_length=30)
    note: str = Field(default='')


class SupplierEvaluation(SupplierEvaluationBase, table=True):
    __tablename__ = 'supplier_evaluations'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SupplierEvaluationCreate(SupplierEvaluationBase):
    pass


class SupplierEvaluationUpdate(SQLModel):
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    period: Optional[str] = None
    otd_score: Optional[float] = None
    quality_score: Optional[float] = None
    cost_score: Optional[float] = None
    overall_rating: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- PurchaseOrder ---

class PurchaseOrderBase(SQLModel):
    po_number: str = Field(index=True, max_length=50)
    supplier_id: Optional[int] = Field(default=None)
    supplier_name: str = Field(default='', max_length=200)
    total_amount: float = Field(default=0)
    currency: str = Field(default='TWD', max_length=10)
    order_date: str = Field(default='')
    eta: str = Field(default='')
    status: str = Field(default='draft', max_length=30)
    approval_status: str = Field(default='pending', max_length=30)
    note: str = Field(default='')


class PurchaseOrder(PurchaseOrderBase, table=True):
    __tablename__ = 'purchase_orders'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PurchaseOrderCreate(PurchaseOrderBase):
    pass


class PurchaseOrderUpdate(SQLModel):
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    order_date: Optional[str] = None
    eta: Optional[str] = None
    status: Optional[str] = None
    approval_status: Optional[str] = None
    note: Optional[str] = None


# --- IqcInspection ---

class IqcInspectionBase(SQLModel):
    inspection_number: str = Field(index=True, max_length=50)
    po_id: Optional[int] = Field(default=None)
    material_name: str = Field(default='', max_length=200)
    lot_size: int = Field(default=0)
    sample_size: int = Field(default=0)
    pass_qty: int = Field(default=0)
    fail_qty: int = Field(default=0)
    result: str = Field(default='pending', max_length=30)
    inspector: str = Field(default='', max_length=100)
    note: str = Field(default='')


class IqcInspection(IqcInspectionBase, table=True):
    __tablename__ = 'iqc_inspections'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IqcInspectionCreate(IqcInspectionBase):
    pass


class IqcInspectionUpdate(SQLModel):
    po_id: Optional[int] = None
    material_name: Optional[str] = None
    lot_size: Optional[int] = None
    sample_size: Optional[int] = None
    pass_qty: Optional[int] = None
    fail_qty: Optional[int] = None
    result: Optional[str] = None
    inspector: Optional[str] = None
    note: Optional[str] = None


# --- RfqEvent ---

class RfqEventBase(SQLModel):
    rfq_number: str = Field(index=True, max_length=50)
    item_name: str = Field(default='', max_length=200)
    quantity: int = Field(default=0)
    bid_count: int = Field(default=0)
    best_price: float = Field(default=0)
    status: str = Field(default='open', max_length=30)
    deadline: str = Field(default='')
    note: str = Field(default='')


class RfqEvent(RfqEventBase, table=True):
    __tablename__ = 'rfq_events'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RfqEventCreate(RfqEventBase):
    pass


class RfqEventUpdate(SQLModel):
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    bid_count: Optional[int] = None
    best_price: Optional[float] = None
    status: Optional[str] = None
    deadline: Optional[str] = None
    note: Optional[str] = None


# --- VmiInventory ---

class VmiInventoryBase(SQLModel):
    vmi_number: str = Field(index=True, max_length=50)
    material_id: Optional[int] = Field(default=None)
    material_name: str = Field(default='', max_length=200)
    supplier_id: Optional[int] = Field(default=None)
    current_qty: float = Field(default=0)
    min_qty: float = Field(default=0)
    max_qty: float = Field(default=0)
    coverage_days: int = Field(default=0)
    status: str = Field(default='normal', max_length=30)
    note: str = Field(default='')


class VmiInventory(VmiInventoryBase, table=True):
    __tablename__ = 'vmi_inventory'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VmiInventoryCreate(VmiInventoryBase):
    pass


class VmiInventoryUpdate(SQLModel):
    material_id: Optional[int] = None
    material_name: Optional[str] = None
    supplier_id: Optional[int] = None
    current_qty: Optional[float] = None
    min_qty: Optional[float] = None
    max_qty: Optional[float] = None
    coverage_days: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- VendorDocument ---

class VendorDocumentBase(SQLModel):
    doc_number: str = Field(index=True, max_length=50)
    supplier_id: Optional[int] = Field(default=None)
    supplier_name: str = Field(default='', max_length=200)
    doc_type: str = Field(default='', max_length=50)
    file_name: str = Field(default='', max_length=200)
    expiry_date: Optional[str] = Field(default=None)
    status: str = Field(default='active', max_length=30)
    note: str = Field(default='')


class VendorDocument(VendorDocumentBase, table=True):
    __tablename__ = 'vendor_documents'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VendorDocumentCreate(VendorDocumentBase):
    pass


class VendorDocumentUpdate(SQLModel):
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    doc_type: Optional[str] = None
    file_name: Optional[str] = None
    expiry_date: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
