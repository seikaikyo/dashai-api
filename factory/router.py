"""Smart Factory - 路由匯出"""
from fastapi import APIRouter
from sqlmodel import Session

from database import engine, get_session
from factory.routes.crud_factory import generate_crud_router
from factory.services.seed_data import seed_all

# Import ALL models (triggers table registration)
from factory.models import *  # noqa: F401, F403


def _r(model, create, update, prefix, tag):
    return generate_crud_router(
        model=model, create_model=create, update_model=update,
        prefix=prefix, tags=[tag],
    )


def init_factory():
    """初始化 factory seed data"""
    with Session(engine) as session:
        seed_all(session)


# 主路由
router = APIRouter()

# ==================== Master (7) ====================
from factory.models.master import (
    Product, ProductCreate, ProductUpdate,
    Material, MaterialCreate, MaterialUpdate,
    Customer, CustomerCreate, CustomerUpdate,
    Supplier, SupplierCreate, SupplierUpdate,
    Equipment, EquipmentCreate, EquipmentUpdate,
    Employee, EmployeeCreate, EmployeeUpdate,
    Location, LocationCreate, LocationUpdate,
)
router.include_router(_r(Product, ProductCreate, ProductUpdate, '/master/products', 'Factory - Master'), prefix='/api/v1')
router.include_router(_r(Material, MaterialCreate, MaterialUpdate, '/master/materials', 'Factory - Master'), prefix='/api/v1')
router.include_router(_r(Customer, CustomerCreate, CustomerUpdate, '/master/customers', 'Factory - Master'), prefix='/api/v1')
router.include_router(_r(Supplier, SupplierCreate, SupplierUpdate, '/master/suppliers', 'Factory - Master'), prefix='/api/v1')
router.include_router(_r(Equipment, EquipmentCreate, EquipmentUpdate, '/master/equipment', 'Factory - Master'), prefix='/api/v1')
router.include_router(_r(Employee, EmployeeCreate, EmployeeUpdate, '/master/employees', 'Factory - Master'), prefix='/api/v1')
router.include_router(_r(Location, LocationCreate, LocationUpdate, '/master/locations', 'Factory - Master'), prefix='/api/v1')

# ==================== Stage 1: Order (7) ====================
from factory.models.order import (
    SalesOrder, SalesOrderCreate, SalesOrderUpdate,
    SalesOrderLine, SalesOrderLineCreate, SalesOrderLineUpdate,
    Quotation, QuotationCreate, QuotationUpdate,
    AtpCheck, AtpCheckCreate, AtpCheckUpdate,
    EdiTransaction, EdiTransactionCreate, EdiTransactionUpdate,
    Configuration, ConfigurationCreate, ConfigurationUpdate,
    CreditReview, CreditReviewCreate, CreditReviewUpdate,
)
router.include_router(_r(SalesOrder, SalesOrderCreate, SalesOrderUpdate, '/order/sales-orders', 'Factory - Order'), prefix='/api/v1')
router.include_router(_r(SalesOrderLine, SalesOrderLineCreate, SalesOrderLineUpdate, '/order/so-lines', 'Factory - Order'), prefix='/api/v1')
router.include_router(_r(Quotation, QuotationCreate, QuotationUpdate, '/order/quotations', 'Factory - Order'), prefix='/api/v1')
router.include_router(_r(AtpCheck, AtpCheckCreate, AtpCheckUpdate, '/order/atp', 'Factory - Order'), prefix='/api/v1')
router.include_router(_r(EdiTransaction, EdiTransactionCreate, EdiTransactionUpdate, '/order/edi', 'Factory - Order'), prefix='/api/v1')
router.include_router(_r(Configuration, ConfigurationCreate, ConfigurationUpdate, '/order/configurations', 'Factory - Order'), prefix='/api/v1')
router.include_router(_r(CreditReview, CreditReviewCreate, CreditReviewUpdate, '/order/credit-reviews', 'Factory - Order'), prefix='/api/v1')

# ==================== Stage 2: Planning (6) ====================
from factory.models.planning import (
    ProductionSchedule, ProductionScheduleCreate, ProductionScheduleUpdate,
    MaterialRequirement, MaterialRequirementCreate, MaterialRequirementUpdate,
    CapacityPlan, CapacityPlanCreate, CapacityPlanUpdate,
    SopPlan, SopPlanCreate, SopPlanUpdate,
    MasterSchedule, MasterScheduleCreate, MasterScheduleUpdate,
    FiniteSchedule, FiniteScheduleCreate, FiniteScheduleUpdate,
)
router.include_router(_r(ProductionSchedule, ProductionScheduleCreate, ProductionScheduleUpdate, '/planning/schedules', 'Factory - Planning'), prefix='/api/v1')
router.include_router(_r(MaterialRequirement, MaterialRequirementCreate, MaterialRequirementUpdate, '/planning/mrp', 'Factory - Planning'), prefix='/api/v1')
router.include_router(_r(CapacityPlan, CapacityPlanCreate, CapacityPlanUpdate, '/planning/capacity', 'Factory - Planning'), prefix='/api/v1')
router.include_router(_r(SopPlan, SopPlanCreate, SopPlanUpdate, '/planning/sop', 'Factory - Planning'), prefix='/api/v1')
router.include_router(_r(MasterSchedule, MasterScheduleCreate, MasterScheduleUpdate, '/planning/mps', 'Factory - Planning'), prefix='/api/v1')
router.include_router(_r(FiniteSchedule, FiniteScheduleCreate, FiniteScheduleUpdate, '/planning/finite', 'Factory - Planning'), prefix='/api/v1')

# ==================== Stage 3: Procurement (6) ====================
from factory.models.procurement import (
    SupplierEvaluation, SupplierEvaluationCreate, SupplierEvaluationUpdate,
    PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate,
    IqcInspection, IqcInspectionCreate, IqcInspectionUpdate,
    RfqEvent, RfqEventCreate, RfqEventUpdate,
    VmiInventory, VmiInventoryCreate, VmiInventoryUpdate,
    VendorDocument, VendorDocumentCreate, VendorDocumentUpdate,
)
router.include_router(_r(SupplierEvaluation, SupplierEvaluationCreate, SupplierEvaluationUpdate, '/procurement/supplier-eval', 'Factory - Procurement'), prefix='/api/v1')
router.include_router(_r(PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate, '/procurement/purchase-orders', 'Factory - Procurement'), prefix='/api/v1')
router.include_router(_r(IqcInspection, IqcInspectionCreate, IqcInspectionUpdate, '/procurement/iqc', 'Factory - Procurement'), prefix='/api/v1')
router.include_router(_r(RfqEvent, RfqEventCreate, RfqEventUpdate, '/procurement/rfq', 'Factory - Procurement'), prefix='/api/v1')
router.include_router(_r(VmiInventory, VmiInventoryCreate, VmiInventoryUpdate, '/procurement/vmi', 'Factory - Procurement'), prefix='/api/v1')
router.include_router(_r(VendorDocument, VendorDocumentCreate, VendorDocumentUpdate, '/procurement/vendor-docs', 'Factory - Procurement'), prefix='/api/v1')

# ==================== Stage 4: Warehouse (6) ====================
from factory.models.warehouse import (
    InventoryTransaction, InventoryTransactionCreate, InventoryTransactionUpdate,
    AgvTask, AgvTaskCreate, AgvTaskUpdate,
    RfidEvent, RfidEventCreate, RfidEventUpdate,
    AsrsOperation, AsrsOperationCreate, AsrsOperationUpdate,
    PtlPick, PtlPickCreate, PtlPickUpdate,
    CrossdockOperation, CrossdockOperationCreate, CrossdockOperationUpdate,
)
router.include_router(_r(InventoryTransaction, InventoryTransactionCreate, InventoryTransactionUpdate, '/warehouse/inventory', 'Factory - Warehouse'), prefix='/api/v1')
router.include_router(_r(AgvTask, AgvTaskCreate, AgvTaskUpdate, '/warehouse/agv-tasks', 'Factory - Warehouse'), prefix='/api/v1')
router.include_router(_r(RfidEvent, RfidEventCreate, RfidEventUpdate, '/warehouse/rfid', 'Factory - Warehouse'), prefix='/api/v1')
router.include_router(_r(AsrsOperation, AsrsOperationCreate, AsrsOperationUpdate, '/warehouse/asrs', 'Factory - Warehouse'), prefix='/api/v1')
router.include_router(_r(PtlPick, PtlPickCreate, PtlPickUpdate, '/warehouse/ptl', 'Factory - Warehouse'), prefix='/api/v1')
router.include_router(_r(CrossdockOperation, CrossdockOperationCreate, CrossdockOperationUpdate, '/warehouse/crossdock', 'Factory - Warehouse'), prefix='/api/v1')

# ==================== Stage 5: Production (6) ====================
from factory.models.production import (
    WorkOrder, WorkOrderCreate, WorkOrderUpdate,
    ScadaReading, ScadaReadingCreate, ScadaReadingUpdate,
    PlcProgram, PlcProgramCreate, PlcProgramUpdate,
    DcsLoop, DcsLoopCreate, DcsLoopUpdate,
    OpcuaNode, OpcuaNodeCreate, OpcuaNodeUpdate,
    HistorianTag, HistorianTagCreate, HistorianTagUpdate,
)
router.include_router(_r(WorkOrder, WorkOrderCreate, WorkOrderUpdate, '/production/work-orders', 'Factory - Production'), prefix='/api/v1')
router.include_router(_r(ScadaReading, ScadaReadingCreate, ScadaReadingUpdate, '/production/scada', 'Factory - Production'), prefix='/api/v1')
router.include_router(_r(PlcProgram, PlcProgramCreate, PlcProgramUpdate, '/production/plc', 'Factory - Production'), prefix='/api/v1')
router.include_router(_r(DcsLoop, DcsLoopCreate, DcsLoopUpdate, '/production/dcs', 'Factory - Production'), prefix='/api/v1')
router.include_router(_r(OpcuaNode, OpcuaNodeCreate, OpcuaNodeUpdate, '/production/opcua', 'Factory - Production'), prefix='/api/v1')
router.include_router(_r(HistorianTag, HistorianTagCreate, HistorianTagUpdate, '/production/historian', 'Factory - Production'), prefix='/api/v1')

# ==================== Stage 6: Quality (6) ====================
from factory.models.quality import (
    NcrRecord, NcrRecordCreate, NcrRecordUpdate,
    SpcMeasurement, SpcMeasurementCreate, SpcMeasurementUpdate,
    AoiInspection, AoiInspectionCreate, AoiInspectionUpdate,
    LabSample, LabSampleCreate, LabSampleUpdate,
    FmeaAnalysis, FmeaAnalysisCreate, FmeaAnalysisUpdate,
    EightdReport, EightdReportCreate, EightdReportUpdate,
)
router.include_router(_r(NcrRecord, NcrRecordCreate, NcrRecordUpdate, '/quality/ncr', 'Factory - Quality'), prefix='/api/v1')
router.include_router(_r(SpcMeasurement, SpcMeasurementCreate, SpcMeasurementUpdate, '/quality/spc', 'Factory - Quality'), prefix='/api/v1')
router.include_router(_r(AoiInspection, AoiInspectionCreate, AoiInspectionUpdate, '/quality/aoi', 'Factory - Quality'), prefix='/api/v1')
router.include_router(_r(LabSample, LabSampleCreate, LabSampleUpdate, '/quality/lims', 'Factory - Quality'), prefix='/api/v1')
router.include_router(_r(FmeaAnalysis, FmeaAnalysisCreate, FmeaAnalysisUpdate, '/quality/fmea', 'Factory - Quality'), prefix='/api/v1')
router.include_router(_r(EightdReport, EightdReportCreate, EightdReportUpdate, '/quality/eightd', 'Factory - Quality'), prefix='/api/v1')

# ==================== Stage 7: Packing (6) ====================
from factory.models.packing import (
    PackingOrder, PackingOrderCreate, PackingOrderUpdate,
    LabelJob, LabelJobCreate, LabelJobUpdate,
    PalletRecord, PalletRecordCreate, PalletRecordUpdate,
    SerialNumber, SerialNumberCreate, SerialNumberUpdate,
    WeightCheck, WeightCheckCreate, WeightCheckUpdate,
    TraceEvent, TraceEventCreate, TraceEventUpdate,
)
router.include_router(_r(PackingOrder, PackingOrderCreate, PackingOrderUpdate, '/packing/orders', 'Factory - Packing'), prefix='/api/v1')
router.include_router(_r(LabelJob, LabelJobCreate, LabelJobUpdate, '/packing/labels', 'Factory - Packing'), prefix='/api/v1')
router.include_router(_r(PalletRecord, PalletRecordCreate, PalletRecordUpdate, '/packing/pallets', 'Factory - Packing'), prefix='/api/v1')
router.include_router(_r(SerialNumber, SerialNumberCreate, SerialNumberUpdate, '/packing/serials', 'Factory - Packing'), prefix='/api/v1')
router.include_router(_r(WeightCheck, WeightCheckCreate, WeightCheckUpdate, '/packing/weights', 'Factory - Packing'), prefix='/api/v1')
router.include_router(_r(TraceEvent, TraceEventCreate, TraceEventUpdate, '/packing/trace', 'Factory - Packing'), prefix='/api/v1')

# ==================== Stage 8: Shipping (6) ====================
from factory.models.shipping import (
    Shipment, ShipmentCreate, ShipmentUpdate,
    DockSchedule, DockScheduleCreate, DockScheduleUpdate,
    TrackingEvent, TrackingEventCreate, TrackingEventUpdate,
    CustomsDeclaration, CustomsDeclarationCreate, CustomsDeclarationUpdate,
    CarrierRate, CarrierRateCreate, CarrierRateUpdate,
    DeliveryProof, DeliveryProofCreate, DeliveryProofUpdate,
)
router.include_router(_r(Shipment, ShipmentCreate, ShipmentUpdate, '/shipping/shipments', 'Factory - Shipping'), prefix='/api/v1')
router.include_router(_r(DockSchedule, DockScheduleCreate, DockScheduleUpdate, '/shipping/dock', 'Factory - Shipping'), prefix='/api/v1')
router.include_router(_r(TrackingEvent, TrackingEventCreate, TrackingEventUpdate, '/shipping/tracking', 'Factory - Shipping'), prefix='/api/v1')
router.include_router(_r(CustomsDeclaration, CustomsDeclarationCreate, CustomsDeclarationUpdate, '/shipping/customs', 'Factory - Shipping'), prefix='/api/v1')
router.include_router(_r(CarrierRate, CarrierRateCreate, CarrierRateUpdate, '/shipping/carriers', 'Factory - Shipping'), prefix='/api/v1')
router.include_router(_r(DeliveryProof, DeliveryProofCreate, DeliveryProofUpdate, '/shipping/pod', 'Factory - Shipping'), prefix='/api/v1')

# ==================== Stage 9: Service (6) ====================
from factory.models.service import (
    ServiceTicket, ServiceTicketCreate, ServiceTicketUpdate,
    RmaRequest, RmaRequestCreate, RmaRequestUpdate,
    FeedbackSurvey, FeedbackSurveyCreate, FeedbackSurveyUpdate,
    FieldOrder, FieldOrderCreate, FieldOrderUpdate,
    KbArticle, KbArticleCreate, KbArticleUpdate,
    WarrantyClaim, WarrantyClaimCreate, WarrantyClaimUpdate,
)
router.include_router(_r(ServiceTicket, ServiceTicketCreate, ServiceTicketUpdate, '/service/tickets', 'Factory - Service'), prefix='/api/v1')
router.include_router(_r(RmaRequest, RmaRequestCreate, RmaRequestUpdate, '/service/rma', 'Factory - Service'), prefix='/api/v1')
router.include_router(_r(FeedbackSurvey, FeedbackSurveyCreate, FeedbackSurveyUpdate, '/service/feedback', 'Factory - Service'), prefix='/api/v1')
router.include_router(_r(FieldOrder, FieldOrderCreate, FieldOrderUpdate, '/service/field-orders', 'Factory - Service'), prefix='/api/v1')
router.include_router(_r(KbArticle, KbArticleCreate, KbArticleUpdate, '/service/kb', 'Factory - Service'), prefix='/api/v1')
router.include_router(_r(WarrantyClaim, WarrantyClaimCreate, WarrantyClaimUpdate, '/service/warranty', 'Factory - Service'), prefix='/api/v1')

# ==================== Dashboard + AI ====================
from factory.routes.dashboard import router as dashboard_router
from factory.routes.ai_chat import router as ai_router
router.include_router(dashboard_router, prefix='/api/v1')
router.include_router(ai_router, prefix='/api/v1')

# ==================== Admin ====================
@router.post('/api/v1/seed/reset', tags=['Factory - Admin'])
def reset_seed():
    from sqlmodel import SQLModel
    from database import engine, create_db_and_tables
    SQLModel.metadata.drop_all(engine)
    create_db_and_tables()
    with Session(engine) as session:
        seed_all(session)
    return {'success': True, 'message': 'Demo data reset complete'}
