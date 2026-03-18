from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class WorkOrderBase(SQLModel):
    wo_number: str = Field(index=True, max_length=50)
    product_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    quantity: int = Field(default=0)
    completed_qty: int = Field(default=0)
    scrap_qty: int = Field(default=0)
    line: str = Field(default='', max_length=50)
    priority: str = Field(default='normal', max_length=20)
    status: str = Field(default='created', max_length=30)
    planned_start: Optional[str] = Field(default=None)
    planned_end: Optional[str] = Field(default=None)
    actual_start: Optional[str] = Field(default=None)
    actual_end: Optional[str] = Field(default=None)
    sales_order_id: Optional[int] = Field(default=None)
    schedule_id: Optional[int] = Field(default=None)
    note: str = Field(default='')


class WorkOrder(WorkOrderBase, table=True):
    __tablename__ = 'work_orders'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderUpdate(SQLModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    completed_qty: Optional[int] = None
    scrap_qty: Optional[int] = None
    line: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    planned_start: Optional[str] = None
    planned_end: Optional[str] = None
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    note: Optional[str] = None


# --- ScadaReading ---

class ScadaReadingBase(SQLModel):
    reading_id: str = Field(index=True, max_length=50)
    equipment_id: Optional[int] = Field(default=None)
    equipment_name: str = Field(default='', max_length=200)
    tag_name: str = Field(default='', max_length=100)
    value: float = Field(default=0)
    unit: str = Field(default='', max_length=30)
    quality: str = Field(default='good', max_length=30)
    timestamp: str = Field(default='', max_length=50)
    note: str = Field(default='')


class ScadaReading(ScadaReadingBase, table=True):
    __tablename__ = 'scada_readings'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ScadaReadingCreate(ScadaReadingBase):
    pass


class ScadaReadingUpdate(SQLModel):
    equipment_id: Optional[int] = None
    equipment_name: Optional[str] = None
    tag_name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    quality: Optional[str] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None


# --- PlcProgram ---

class PlcProgramBase(SQLModel):
    program_id: str = Field(index=True, max_length=50)
    equipment_id: Optional[int] = Field(default=None)
    equipment_name: str = Field(default='', max_length=200)
    program_name: str = Field(default='', max_length=200)
    version: str = Field(default='1.0', max_length=20)
    language: str = Field(default='Ladder', max_length=30)
    status: str = Field(default='active', max_length=30)
    last_download: Optional[str] = Field(default=None)
    note: str = Field(default='')


class PlcProgram(PlcProgramBase, table=True):
    __tablename__ = 'plc_programs'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlcProgramCreate(PlcProgramBase):
    pass


class PlcProgramUpdate(SQLModel):
    equipment_id: Optional[int] = None
    equipment_name: Optional[str] = None
    program_name: Optional[str] = None
    version: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None
    last_download: Optional[str] = None
    note: Optional[str] = None


# --- DcsLoop ---

class DcsLoopBase(SQLModel):
    loop_id: str = Field(index=True, max_length=50)
    loop_name: str = Field(default='', max_length=200)
    process_variable: str = Field(default='', max_length=100)
    setpoint: float = Field(default=0)
    actual_value: float = Field(default=0)
    output_pct: float = Field(default=0)
    mode: str = Field(default='auto', max_length=20)
    status: str = Field(default='running', max_length=30)
    note: str = Field(default='')


class DcsLoop(DcsLoopBase, table=True):
    __tablename__ = 'dcs_loops'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DcsLoopCreate(DcsLoopBase):
    pass


class DcsLoopUpdate(SQLModel):
    loop_name: Optional[str] = None
    process_variable: Optional[str] = None
    setpoint: Optional[float] = None
    actual_value: Optional[float] = None
    output_pct: Optional[float] = None
    mode: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- OpcuaNode ---

class OpcuaNodeBase(SQLModel):
    node_id: str = Field(index=True, max_length=100)
    display_name: str = Field(default='', max_length=200)
    data_type: str = Field(default='Float', max_length=30)
    value: str = Field(default='', max_length=200)
    quality: str = Field(default='Good', max_length=30)
    server: str = Field(default='', max_length=200)
    timestamp: str = Field(default='', max_length=50)
    note: str = Field(default='')


class OpcuaNode(OpcuaNodeBase, table=True):
    __tablename__ = 'opcua_nodes'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OpcuaNodeCreate(OpcuaNodeBase):
    pass


class OpcuaNodeUpdate(SQLModel):
    display_name: Optional[str] = None
    data_type: Optional[str] = None
    value: Optional[str] = None
    quality: Optional[str] = None
    server: Optional[str] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None


# --- HistorianTag ---

class HistorianTagBase(SQLModel):
    tag_id: str = Field(index=True, max_length=100)
    tag_name: str = Field(default='', max_length=200)
    source: str = Field(default='', max_length=100)
    current_value: float = Field(default=0)
    min_24h: float = Field(default=0)
    max_24h: float = Field(default=0)
    avg_24h: float = Field(default=0)
    sample_count: int = Field(default=0)
    note: str = Field(default='')


class HistorianTag(HistorianTagBase, table=True):
    __tablename__ = 'historian_tags'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class HistorianTagCreate(HistorianTagBase):
    pass


class HistorianTagUpdate(SQLModel):
    tag_name: Optional[str] = None
    source: Optional[str] = None
    current_value: Optional[float] = None
    min_24h: Optional[float] = None
    max_24h: Optional[float] = None
    avg_24h: Optional[float] = None
    sample_count: Optional[int] = None
    note: Optional[str] = None
