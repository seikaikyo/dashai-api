from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# --- ProductionSchedule ---

class ProductionScheduleBase(SQLModel):
    schedule_number: str = Field(index=True, max_length=50)
    product_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    quantity: int = Field(default=0)
    line: str = Field(default='', max_length=50)
    planned_start: str = Field(default='')
    planned_end: str = Field(default='')
    priority: str = Field(default='normal', max_length=20)
    status: str = Field(default='draft', max_length=30)
    sales_order_id: Optional[int] = Field(default=None)
    note: str = Field(default='')


class ProductionSchedule(ProductionScheduleBase, table=True):
    __tablename__ = 'production_schedules'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProductionScheduleCreate(ProductionScheduleBase):
    pass


class ProductionScheduleUpdate(SQLModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    line: Optional[str] = None
    planned_start: Optional[str] = None
    planned_end: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    sales_order_id: Optional[int] = None
    note: Optional[str] = None


# --- MaterialRequirement ---

class MaterialRequirementBase(SQLModel):
    mrp_number: str = Field(index=True, max_length=50)
    material_id: Optional[int] = Field(default=None)
    material_name: str = Field(default='', max_length=200)
    required_qty: float = Field(default=0)
    on_hand_qty: float = Field(default=0)
    net_qty: float = Field(default=0)
    action: str = Field(default='purchase', max_length=30)
    due_date: str = Field(default='')
    status: str = Field(default='planned', max_length=30)
    note: str = Field(default='')


class MaterialRequirement(MaterialRequirementBase, table=True):
    __tablename__ = 'material_requirements'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialRequirementCreate(MaterialRequirementBase):
    pass


class MaterialRequirementUpdate(SQLModel):
    material_id: Optional[int] = None
    material_name: Optional[str] = None
    required_qty: Optional[float] = None
    on_hand_qty: Optional[float] = None
    net_qty: Optional[float] = None
    action: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- CapacityPlan ---

class CapacityPlanBase(SQLModel):
    plan_number: str = Field(index=True, max_length=50)
    line: str = Field(default='', max_length=50)
    period: str = Field(default='', max_length=30)
    available_hours: float = Field(default=0)
    planned_hours: float = Field(default=0)
    utilization_pct: float = Field(default=0)
    bottleneck: bool = Field(default=False)
    status: str = Field(default='draft', max_length=30)
    note: str = Field(default='')


class CapacityPlan(CapacityPlanBase, table=True):
    __tablename__ = 'capacity_plans'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CapacityPlanCreate(CapacityPlanBase):
    pass


class CapacityPlanUpdate(SQLModel):
    line: Optional[str] = None
    period: Optional[str] = None
    available_hours: Optional[float] = None
    planned_hours: Optional[float] = None
    utilization_pct: Optional[float] = None
    bottleneck: Optional[bool] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- SopPlan ---

class SopPlanBase(SQLModel):
    plan_number: str = Field(index=True, max_length=50)
    period: str = Field(default='', max_length=30)
    demand_qty: int = Field(default=0)
    supply_qty: int = Field(default=0)
    gap: int = Field(default=0)
    action: str = Field(default='')
    status: str = Field(default='draft', max_length=30)
    note: str = Field(default='')


class SopPlan(SopPlanBase, table=True):
    __tablename__ = 'sop_plans'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SopPlanCreate(SopPlanBase):
    pass


class SopPlanUpdate(SQLModel):
    period: Optional[str] = None
    demand_qty: Optional[int] = None
    supply_qty: Optional[int] = None
    gap: Optional[int] = None
    action: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- MasterSchedule ---

class MasterScheduleBase(SQLModel):
    mps_number: str = Field(index=True, max_length=50)
    product_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    week: str = Field(default='', max_length=20)
    quantity: int = Field(default=0)
    source: str = Field(default='forecast', max_length=30)
    status: str = Field(default='planned', max_length=30)
    note: str = Field(default='')


class MasterSchedule(MasterScheduleBase, table=True):
    __tablename__ = 'master_schedules'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MasterScheduleCreate(MasterScheduleBase):
    pass


class MasterScheduleUpdate(SQLModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    week: Optional[str] = None
    quantity: Optional[int] = None
    source: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- FiniteSchedule ---

class FiniteScheduleBase(SQLModel):
    fs_number: str = Field(index=True, max_length=50)
    work_order_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    line: str = Field(default='', max_length=50)
    start_time: str = Field(default='')
    end_time: str = Field(default='')
    setup_minutes: int = Field(default=0)
    status: str = Field(default='scheduled', max_length=30)
    note: str = Field(default='')


class FiniteSchedule(FiniteScheduleBase, table=True):
    __tablename__ = 'finite_schedules'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FiniteScheduleCreate(FiniteScheduleBase):
    pass


class FiniteScheduleUpdate(SQLModel):
    work_order_id: Optional[int] = None
    product_name: Optional[str] = None
    line: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    setup_minutes: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None
