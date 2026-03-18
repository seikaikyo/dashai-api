from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class NcrRecordBase(SQLModel):
    ncr_number: str = Field(index=True, max_length=50)
    product_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    work_order_id: Optional[int] = Field(default=None)
    defect_type: str = Field(default='', max_length=100)
    severity: str = Field(default='minor', max_length=30)
    status: str = Field(default='open', max_length=30)
    description: str = Field(default='')
    root_cause: str = Field(default='')
    corrective_action: str = Field(default='')
    owner: str = Field(default='', max_length=100)
    detected_at: str = Field(default='', max_length=50)
    closed_at: Optional[str] = Field(default=None)
    note: str = Field(default='')


class NcrRecord(NcrRecordBase, table=True):
    __tablename__ = 'ncr_records'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NcrRecordCreate(NcrRecordBase):
    pass


class NcrRecordUpdate(SQLModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    work_order_id: Optional[int] = None
    defect_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    owner: Optional[str] = None
    detected_at: Optional[str] = None
    closed_at: Optional[str] = None
    note: Optional[str] = None


# --- SpcMeasurement ---

class SpcMeasurementBase(SQLModel):
    measurement_id: str = Field(index=True, max_length=50)
    work_order_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    parameter: str = Field(default='', max_length=100)
    value: float = Field(default=0)
    usl: float = Field(default=0)
    lsl: float = Field(default=0)
    in_control: bool = Field(default=True)
    timestamp: str = Field(default='', max_length=50)
    note: str = Field(default='')


class SpcMeasurement(SpcMeasurementBase, table=True):
    __tablename__ = 'spc_measurements'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SpcMeasurementCreate(SpcMeasurementBase):
    pass


class SpcMeasurementUpdate(SQLModel):
    work_order_id: Optional[int] = None
    product_name: Optional[str] = None
    parameter: Optional[str] = None
    value: Optional[float] = None
    usl: Optional[float] = None
    lsl: Optional[float] = None
    in_control: Optional[bool] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None


# --- AoiInspection ---

class AoiInspectionBase(SQLModel):
    inspection_id: str = Field(index=True, max_length=50)
    work_order_id: Optional[int] = Field(default=None)
    product_name: str = Field(default='', max_length=200)
    image_count: int = Field(default=0)
    defect_count: int = Field(default=0)
    defect_types: str = Field(default='', max_length=500)
    result: str = Field(default='pass', max_length=30)
    confidence: float = Field(default=0)
    timestamp: str = Field(default='', max_length=50)
    note: str = Field(default='')


class AoiInspection(AoiInspectionBase, table=True):
    __tablename__ = 'aoi_inspections'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AoiInspectionCreate(AoiInspectionBase):
    pass


class AoiInspectionUpdate(SQLModel):
    work_order_id: Optional[int] = None
    product_name: Optional[str] = None
    image_count: Optional[int] = None
    defect_count: Optional[int] = None
    defect_types: Optional[str] = None
    result: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None


# --- LabSample ---

class LabSampleBase(SQLModel):
    sample_number: str = Field(index=True, max_length=50)
    material_name: str = Field(default='', max_length=200)
    test_item: str = Field(default='', max_length=100)
    result_value: str = Field(default='', max_length=200)
    specification: str = Field(default='', max_length=200)
    result: str = Field(default='pending', max_length=30)
    analyst: str = Field(default='', max_length=100)
    tested_at: Optional[str] = Field(default=None)
    note: str = Field(default='')


class LabSample(LabSampleBase, table=True):
    __tablename__ = 'lab_samples'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LabSampleCreate(LabSampleBase):
    pass


class LabSampleUpdate(SQLModel):
    material_name: Optional[str] = None
    test_item: Optional[str] = None
    result_value: Optional[str] = None
    specification: Optional[str] = None
    result: Optional[str] = None
    analyst: Optional[str] = None
    tested_at: Optional[str] = None
    note: Optional[str] = None


# --- FmeaAnalysis ---

class FmeaAnalysisBase(SQLModel):
    fmea_number: str = Field(index=True, max_length=50)
    process_step: str = Field(default='', max_length=200)
    failure_mode: str = Field(default='', max_length=200)
    severity: int = Field(default=1)
    occurrence: int = Field(default=1)
    detection: int = Field(default=1)
    rpn: int = Field(default=1)
    action_plan: str = Field(default='')
    status: str = Field(default='open', max_length=30)
    note: str = Field(default='')


class FmeaAnalysis(FmeaAnalysisBase, table=True):
    __tablename__ = 'fmea_analyses'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FmeaAnalysisCreate(FmeaAnalysisBase):
    pass


class FmeaAnalysisUpdate(SQLModel):
    process_step: Optional[str] = None
    failure_mode: Optional[str] = None
    severity: Optional[int] = None
    occurrence: Optional[int] = None
    detection: Optional[int] = None
    rpn: Optional[int] = None
    action_plan: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


# --- EightdReport ---

class EightdReportBase(SQLModel):
    report_number: str = Field(index=True, max_length=50)
    ncr_id: Optional[int] = Field(default=None)
    problem_description: str = Field(default='')
    team_members: str = Field(default='')
    containment: str = Field(default='')
    root_cause: str = Field(default='')
    corrective_action: str = Field(default='')
    preventive_action: str = Field(default='')
    status: str = Field(default='D1', max_length=30)
    note: str = Field(default='')


class EightdReport(EightdReportBase, table=True):
    __tablename__ = 'eightd_reports'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EightdReportCreate(EightdReportBase):
    pass


class EightdReportUpdate(SQLModel):
    ncr_id: Optional[int] = None
    problem_description: Optional[str] = None
    team_members: Optional[str] = None
    containment: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
