from sqlmodel import Session, select
from factory.models.master import (
    Product, Material, Customer, Supplier,
    Equipment, Employee, Location,
)
from factory.models.production import WorkOrder
from factory.models.order import SalesOrder, SalesOrderLine
from factory.models.planning import ProductionSchedule
from factory.models.procurement import PurchaseOrder
from factory.models.warehouse import InventoryTransaction
from factory.models.quality import NcrRecord
from factory.models.packing import PackingOrder
from factory.models.shipping import Shipment
from factory.models.service import ServiceTicket


def seed_all(session: Session):
    existing = session.exec(select(Product).limit(1)).first()
    if existing:
        return False

    _seed_products(session)
    _seed_materials(session)
    _seed_customers(session)
    _seed_suppliers(session)
    _seed_equipment(session)
    _seed_employees(session)
    _seed_locations(session)
    _seed_sales_orders(session)
    _seed_production_schedules(session)
    _seed_purchase_orders(session)
    _seed_inventory_transactions(session)
    _seed_work_orders(session)
    _seed_ncr_records(session)
    _seed_packing_orders(session)
    _seed_shipments(session)
    _seed_service_tickets(session)
    session.commit()
    return True


def _seed_products(s: Session):
    items = [
        Product(code='PCB-Module-A', name='PCB 主板模組 A', category='PCBA', unit='PCS', standard_cost=45.0, lead_time_days=5),
        Product(code='Sensor-Kit-B', name='感測器套件 B', category='Sensor', unit='SET', standard_cost=28.0, lead_time_days=3),
        Product(code='Controller-C', name='控制器 C', category='Controller', unit='PCS', standard_cost=120.0, lead_time_days=7),
        Product(code='Cable-Set-D', name='線材組 D', category='Cable', unit='SET', standard_cost=8.5, lead_time_days=2),
        Product(code='Housing-E', name='機殼 E', category='Mechanical', unit='PCS', standard_cost=15.0, lead_time_days=4),
        Product(code='Power-Supply-F', name='電源供應器 F', category='Power', unit='PCS', standard_cost=35.0, lead_time_days=5),
        Product(code='Display-Module-G', name='顯示模組 G', category='Display', unit='PCS', standard_cost=62.0, lead_time_days=6),
        Product(code='Motor-Drive-H', name='馬達驅動器 H', category='Drive', unit='PCS', standard_cost=88.0, lead_time_days=8),
        Product(code='IO-Board-I', name='I/O 擴充板 I', category='PCBA', unit='PCS', standard_cost=22.0, lead_time_days=4),
        Product(code='Comm-Module-J', name='通訊模組 J', category='Communication', unit='PCS', standard_cost=38.0, lead_time_days=5),
    ]
    for item in items:
        s.add(item)


def _seed_materials(s: Session):
    items = [
        Material(code='PCB-FR4-001', name='FR4 基板 1.6mm', category='PCB', unit='PCS', safety_stock=500, reorder_point=200, unit_cost=3.2),
        Material(code='IC-Chip-A01', name='主控 IC A01', category='IC', unit='PCS', safety_stock=2000, reorder_point=800, unit_cost=5.8),
        Material(code='Solder-Paste', name='錫膏 SAC305', category='Consumable', unit='KG', safety_stock=20, reorder_point=10, unit_cost=85.0),
        Material(code='Connector-USB', name='USB-C 連接器', category='Connector', unit='PCS', safety_stock=3000, reorder_point=1000, unit_cost=0.45),
        Material(code='Resistor-Pack', name='電阻包 0402', category='Passive', unit='REEL', safety_stock=50, reorder_point=20, unit_cost=12.0),
        Material(code='Capacitor-MLCC', name='MLCC 電容 0603', category='Passive', unit='REEL', safety_stock=40, reorder_point=15, unit_cost=18.0),
        Material(code='LED-White', name='白光 LED 0805', category='LED', unit='REEL', safety_stock=30, reorder_point=10, unit_cost=8.5),
        Material(code='Heat-Sink-AL', name='鋁散熱片', category='Thermal', unit='PCS', safety_stock=500, reorder_point=200, unit_cost=2.1),
        Material(code='Box-M', name='中型包裝箱', category='Packaging', unit='PCS', safety_stock=200, reorder_point=100, unit_cost=1.5),
        Material(code='Bubble-Wrap', name='氣泡布', category='Packaging', unit='M', safety_stock=500, reorder_point=200, unit_cost=0.8),
    ]
    for item in items:
        s.add(item)


def _seed_customers(s: Session):
    items = [
        Customer(code='TSMC', name='台灣積體電路', contact='Wang Ming', email='wang@tsmc.com', phone='03-5636688', address='新竹科學園區', credit_limit=5000000, payment_terms='NET60'),
        Customer(code='UMC', name='聯華電子', contact='Lee Hui', email='lee@umc.com', phone='03-5782258', address='新竹科學園區', credit_limit=3000000, payment_terms='NET45'),
        Customer(code='ASE', name='日月光半導體', contact='Chen Yu', email='chen@ase.com', phone='07-3617131', address='高雄楠梓加工區', credit_limit=2000000, payment_terms='NET30'),
        Customer(code='HON-HAI', name='鴻海精密', contact='Zhang Wei', email='zhang@foxconn.com', phone='02-22688000', address='新北市土城區', credit_limit=8000000, payment_terms='NET45'),
        Customer(code='DELTA', name='台達電子', contact='Lin Fang', email='lin@delta.com', phone='02-87972088', address='台北市內湖區', credit_limit=2500000, payment_terms='NET30'),
    ]
    for item in items:
        s.add(item)


def _seed_suppliers(s: Session):
    items = [
        Supplier(code='SUP-PCB-01', name='建鼎科技', contact='Huang Li', email='huang@pcb-supplier.tw', phone='03-4526789', rating='A', lead_time_days=5),
        Supplier(code='SUP-IC-01', name='大聯大', contact='Wu Jian', email='wu@wpg.com', phone='02-26592000', rating='A', lead_time_days=7),
        Supplier(code='SUP-CONN-01', name='正凌精密', contact='Xu Ming', email='xu@connector.tw', phone='04-23591234', rating='B', lead_time_days=3),
        Supplier(code='SUP-PKG-01', name='正隆紙業', contact='Cai Hong', email='cai@clc.com.tw', phone='02-25065600', rating='B', lead_time_days=2),
        Supplier(code='SUP-CHEM-01', name='長春化工', contact='Yang Wen', email='yang@ccpg.com', phone='02-27178888', rating='A', lead_time_days=10),
    ]
    for item in items:
        s.add(item)


def _seed_equipment(s: Session):
    items = [
        Equipment(code='SMT-L1-01', name='SMT 貼片機 Line-1', line='Line-1', equipment_type='SMT', manufacturer='Panasonic', model='NPM-W2S', status='running'),
        Equipment(code='SMT-L2-01', name='SMT 貼片機 Line-2', line='Line-2', equipment_type='SMT', manufacturer='Panasonic', model='NPM-W2S', status='running'),
        Equipment(code='REFLOW-L1', name='迴焊爐 Line-1', line='Line-1', equipment_type='Reflow', manufacturer='Heller', model='1936MK7', status='running'),
        Equipment(code='AOI-L1', name='AOI 檢測機 Line-1', line='Line-1', equipment_type='AOI', manufacturer='Koh Young', model='Zenith', status='running'),
        Equipment(code='CNC-01', name='CNC 加工中心 #1', line='CNC', equipment_type='CNC', manufacturer='Mazak', model='VCN-530C', status='running'),
        Equipment(code='PACK-01', name='自動包裝線 #1', line='Pack', equipment_type='Packing', manufacturer='Sealed Air', model='I-Pack', status='running'),
        Equipment(code='AGV-01', name='AGV 搬運車 #1', line='Warehouse', equipment_type='AGV', manufacturer='MiR', model='MiR250', status='running'),
        Equipment(code='AGV-02', name='AGV 搬運車 #2', line='Warehouse', equipment_type='AGV', manufacturer='MiR', model='MiR250', status='charging'),
    ]
    for item in items:
        s.add(item)


def _seed_employees(s: Session):
    items = [
        Employee(code='EMP-001', name='王大明', department='Production', role='Operator', shift='day', skill_level='L3'),
        Employee(code='EMP-002', name='李小華', department='Production', role='Operator', shift='day', skill_level='L2'),
        Employee(code='EMP-003', name='張志偉', department='Quality', role='Inspector', shift='day', skill_level='L3'),
        Employee(code='EMP-004', name='陳美玲', department='Warehouse', role='Picker', shift='day', skill_level='L2'),
        Employee(code='EMP-005', name='林志鴻', department='Maintenance', role='Technician', shift='day', skill_level='L4'),
        Employee(code='EMP-006', name='黃雅琪', department='Planning', role='Planner', shift='day', skill_level='L3'),
        Employee(code='EMP-007', name='劉建國', department='Shipping', role='Dispatcher', shift='day', skill_level='L2'),
        Employee(code='EMP-008', name='吳佳蓉', department='Service', role='Agent', shift='day', skill_level='L2'),
    ]
    for item in items:
        s.add(item)


def _seed_locations(s: Session):
    items = [
        Location(code='A-01-01', name='A 區 1 排 1 層', warehouse='Main', zone='A', aisle='01', rack='01', level='01', location_type='storage'),
        Location(code='A-01-02', name='A 區 1 排 2 層', warehouse='Main', zone='A', aisle='01', rack='01', level='02', location_type='storage'),
        Location(code='A-02-01', name='A 區 2 排 1 層', warehouse='Main', zone='A', aisle='02', rack='01', level='01', location_type='storage'),
        Location(code='B-01-01', name='B 區 1 排 1 層', warehouse='Main', zone='B', aisle='01', rack='01', level='01', location_type='storage'),
        Location(code='B-02-01', name='B 區 2 排 1 層', warehouse='Main', zone='B', aisle='02', rack='01', level='01', location_type='storage'),
        Location(code='C-01-01', name='C 區冷藏 1', warehouse='Main', zone='C', aisle='01', rack='01', level='01', location_type='cold'),
        Location(code='RECV-01', name='收貨區 1', warehouse='Main', zone='RECV', location_type='receiving'),
        Location(code='SHIP-01', name='出貨區 1', warehouse='Main', zone='SHIP', location_type='shipping'),
        Location(code='QC-HOLD', name='品質待驗區', warehouse='Main', zone='QC', location_type='quarantine'),
        Location(code='STAGING', name='集貨區', warehouse='Main', zone='SHIP', location_type='staging'),
    ]
    for item in items:
        s.add(item)


def _seed_production_schedules(s: Session):
    items = [
        ProductionSchedule(schedule_number='PS-2026-W12-01', product_id=1, product_name='PCB 主板模組 A', quantity=1000, line='Line-1', planned_start='2026-03-15', planned_end='2026-03-20', priority='high', status='released', sales_order_id=1),
        ProductionSchedule(schedule_number='PS-2026-W12-02', product_id=2, product_name='感測器套件 B', quantity=500, line='Line-2', planned_start='2026-03-12', planned_end='2026-03-16', priority='normal', status='completed', sales_order_id=2),
        ProductionSchedule(schedule_number='PS-2026-W13-01', product_id=3, product_name='控制器 C', quantity=200, line='Line-1', planned_start='2026-03-18', planned_end='2026-03-22', priority='urgent', status='draft', sales_order_id=3),
        ProductionSchedule(schedule_number='PS-2026-W11-01', product_id=1, product_name='PCB 主板模組 A', quantity=2000, line='Line-1', planned_start='2026-03-08', planned_end='2026-03-14', priority='high', status='completed', sales_order_id=4),
        ProductionSchedule(schedule_number='PS-2026-W12-03', product_id=4, product_name='線材組 D', quantity=3000, line='Line-2', planned_start='2026-03-16', planned_end='2026-03-21', priority='normal', status='released', sales_order_id=5),
    ]
    for item in items:
        s.add(item)


def _seed_purchase_orders(s: Session):
    items = [
        PurchaseOrder(po_number='PO-2026-0101', supplier_id=1, supplier_name='建鼎科技', total_amount=32000, order_date='2026-03-08', eta='2026-03-13', status='received', approval_status='approved'),
        PurchaseOrder(po_number='PO-2026-0102', supplier_id=2, supplier_name='大聯大', total_amount=58000, order_date='2026-03-10', eta='2026-03-17', status='in_transit', approval_status='approved'),
        PurchaseOrder(po_number='PO-2026-0103', supplier_id=3, supplier_name='正凌精密', total_amount=13500, order_date='2026-03-12', eta='2026-03-15', status='received', approval_status='approved'),
        PurchaseOrder(po_number='PO-2026-0104', supplier_id=4, supplier_name='正隆紙業', total_amount=7500, order_date='2026-03-14', eta='2026-03-16', status='draft', approval_status='pending'),
        PurchaseOrder(po_number='PO-2026-0105', supplier_id=5, supplier_name='長春化工', total_amount=42500, order_date='2026-03-15', eta='2026-03-25', status='confirmed', approval_status='approved'),
    ]
    for item in items:
        s.add(item)


def _seed_inventory_transactions(s: Session):
    items = [
        InventoryTransaction(txn_number='TXN-2026-00501', material_id=1, material_name='FR4 基板 1.6mm', location_code='A-01-01', txn_type='receipt', quantity=1000, reference_type='PO', reference_id=1, operator='Chen Mei-Ling', status='completed'),
        InventoryTransaction(txn_number='TXN-2026-00502', material_id=2, material_name='主控 IC A01', location_code='A-01-02', txn_type='receipt', quantity=2000, reference_type='PO', reference_id=2, operator='Chen Mei-Ling', status='completed'),
        InventoryTransaction(txn_number='TXN-2026-00503', material_id=1, material_name='FR4 基板 1.6mm', location_code='A-01-01', txn_type='issue', quantity=-500, reference_type='WO', reference_id=1, operator='Wang Da-Ming', status='completed'),
        InventoryTransaction(txn_number='TXN-2026-00504', material_id=3, material_name='錫膏 SAC305', location_code='C-01-01', txn_type='receipt', quantity=10, reference_type='PO', reference_id=3, operator='Chen Mei-Ling', status='completed'),
        InventoryTransaction(txn_number='TXN-2026-00505', material_id=4, material_name='USB-C 連接器', location_code='A-02-01', txn_type='receipt', quantity=3000, reference_type='PO', reference_id=3, operator='Chen Mei-Ling', status='completed'),
        InventoryTransaction(txn_number='TXN-2026-00506', material_id=2, material_name='主控 IC A01', location_code='A-01-02', txn_type='issue', quantity=-1000, reference_type='WO', reference_id=4, operator='Wang Da-Ming', status='completed'),
    ]
    for item in items:
        s.add(item)


def _seed_sales_orders(s: Session):
    items = [
        SalesOrder(so_number='SO-2026-0001', customer_id=1, customer_name='台灣積體電路', order_date='2026-03-10', delivery_date='2026-03-25', total_amount=450000, status='confirmed', shipping_address='新竹科學園區'),
        SalesOrder(so_number='SO-2026-0002', customer_id=2, customer_name='聯華電子', order_date='2026-03-12', delivery_date='2026-03-28', total_amount=280000, status='in_production', shipping_address='新竹科學園區'),
        SalesOrder(so_number='SO-2026-0003', customer_id=3, customer_name='日月光半導體', order_date='2026-03-14', delivery_date='2026-04-01', total_amount=120000, status='draft', shipping_address='高雄楠梓加工區'),
        SalesOrder(so_number='SO-2026-0004', customer_id=4, customer_name='鴻海精密', order_date='2026-03-08', delivery_date='2026-03-20', total_amount=880000, status='shipped', shipping_address='新北市土城區'),
        SalesOrder(so_number='SO-2026-0005', customer_id=5, customer_name='台達電子', order_date='2026-03-15', delivery_date='2026-03-30', total_amount=250000, status='confirmed', shipping_address='台北市內湖區'),
        SalesOrder(so_number='SO-2026-0006', customer_id=1, customer_name='台灣積體電路', order_date='2026-03-01', delivery_date='2026-03-15', total_amount=620000, status='shipped', shipping_address='新竹科學園區'),
        SalesOrder(so_number='SO-2026-0007', customer_id=2, customer_name='聯華電子', order_date='2026-03-03', delivery_date='2026-03-18', total_amount=380000, status='shipped', shipping_address='新竹科學園區'),
        SalesOrder(so_number='SO-2026-0008', customer_id=3, customer_name='日月光半導體', order_date='2026-03-05', delivery_date='2026-03-20', total_amount=195000, status='shipped', shipping_address='高雄楠梓加工區'),
        SalesOrder(so_number='SO-2026-0009', customer_id=4, customer_name='鴻海精密', order_date='2026-02-25', delivery_date='2026-03-10', total_amount=1250000, status='shipped', shipping_address='新北市土城區'),
        SalesOrder(so_number='SO-2026-0010', customer_id=5, customer_name='台達電子', order_date='2026-03-16', delivery_date='2026-04-02', total_amount=175000, status='draft', shipping_address='台北市內湖區'),
        SalesOrder(so_number='SO-2026-0011', customer_id=1, customer_name='台灣積體電路', order_date='2026-03-17', delivery_date='2026-04-05', total_amount=530000, status='confirmed', shipping_address='新竹科學園區'),
        SalesOrder(so_number='SO-2026-0012', customer_id=3, customer_name='日月光半導體', order_date='2026-02-20', delivery_date='2026-03-08', total_amount=420000, status='shipped', shipping_address='高雄楠梓加工區'),
    ]
    for item in items:
        s.add(item)


def _seed_work_orders(s: Session):
    items = [
        WorkOrder(wo_number='WO-2026-0001', product_id=1, product_name='PCB 主板模組 A', quantity=1000, completed_qty=850, line='Line-1', priority='high', status='in_progress', planned_start='2026-03-15', planned_end='2026-03-20', actual_start='2026-03-15', sales_order_id=1),
        WorkOrder(wo_number='WO-2026-0002', product_id=2, product_name='感測器套件 B', quantity=500, completed_qty=500, line='Line-2', priority='normal', status='completed', planned_start='2026-03-12', planned_end='2026-03-16', actual_start='2026-03-12', actual_end='2026-03-16', sales_order_id=2),
        WorkOrder(wo_number='WO-2026-0003', product_id=3, product_name='控制器 C', quantity=200, completed_qty=0, line='Line-1', priority='urgent', status='created', planned_start='2026-03-18', planned_end='2026-03-22', sales_order_id=3),
        WorkOrder(wo_number='WO-2026-0004', product_id=1, product_name='PCB 主板模組 A', quantity=2000, completed_qty=2000, scrap_qty=12, line='Line-1', priority='high', status='closed', planned_start='2026-03-08', planned_end='2026-03-14', actual_start='2026-03-08', actual_end='2026-03-13', sales_order_id=4),
        WorkOrder(wo_number='WO-2026-0005', product_id=4, product_name='線材組 D', quantity=3000, completed_qty=1200, line='Line-2', priority='normal', status='in_progress', planned_start='2026-03-16', planned_end='2026-03-21', actual_start='2026-03-16', sales_order_id=2),
        WorkOrder(wo_number='WO-2026-0006', product_id=5, product_name='機殼 E', quantity=800, completed_qty=800, line='Line-1', priority='normal', status='completed', planned_start='2026-03-01', planned_end='2026-03-05', actual_start='2026-03-01', actual_end='2026-03-04', sales_order_id=6),
        WorkOrder(wo_number='WO-2026-0007', product_id=6, product_name='電源供應器 F', quantity=600, completed_qty=600, scrap_qty=3, line='Line-2', priority='high', status='closed', planned_start='2026-03-03', planned_end='2026-03-08', actual_start='2026-03-03', actual_end='2026-03-07', sales_order_id=7),
        WorkOrder(wo_number='WO-2026-0008', product_id=7, product_name='顯示模組 G', quantity=400, completed_qty=400, line='Line-1', priority='normal', status='completed', planned_start='2026-03-05', planned_end='2026-03-10', actual_start='2026-03-05', actual_end='2026-03-09', sales_order_id=8),
        WorkOrder(wo_number='WO-2026-0009', product_id=1, product_name='PCB 主板模組 A', quantity=3000, completed_qty=3000, scrap_qty=8, line='Line-1', priority='urgent', status='closed', planned_start='2026-02-25', planned_end='2026-03-05', actual_start='2026-02-25', actual_end='2026-03-04', sales_order_id=9),
        WorkOrder(wo_number='WO-2026-0010', product_id=8, product_name='馬達驅動器 H', quantity=150, completed_qty=0, line='Line-2', priority='normal', status='created', planned_start='2026-03-20', planned_end='2026-03-25', sales_order_id=11),
    ]
    for item in items:
        s.add(item)


def _seed_ncr_records(s: Session):
    items = [
        NcrRecord(ncr_number='NCR-2026-0342', product_id=1, product_name='PCB 主板模組 A', work_order_id=1, defect_type='Solder bridge', severity='major', status='investigating', description='Line-1 焊接站發現 3 件錫橋', owner='Zhang Zhi-Wei', detected_at='2026-03-17 09:30'),
        NcrRecord(ncr_number='NCR-2026-0341', product_id=5, product_name='機殼 E', defect_type='Scratch', severity='minor', status='containment', description='外觀刮傷 2 件', owner='Lin Mei', detected_at='2026-03-16 14:00'),
        NcrRecord(ncr_number='NCR-2026-0340', product_id=3, product_name='控制器 C', defect_type='Dimension OOS', severity='critical', status='root_cause', description='尺寸超規 0.15mm', owner='Zhang Yu', detected_at='2026-03-15 11:20'),
        NcrRecord(ncr_number='NCR-2026-0339', product_id=4, product_name='線材組 D', defect_type='Label error', severity='minor', status='closed', description='標籤貼錯型號', owner='Wang Li', detected_at='2026-03-14 16:45', closed_at='2026-03-15 10:00'),
    ]
    for item in items:
        s.add(item)


def _seed_packing_orders(s: Session):
    items = [
        PackingOrder(order_number='PKG-2026-0201', work_order_id=2, product_name='感測器套件 B', quantity=500, box_type='M', weight_kg=125.0, operator='Liu Jian-Guo', status='completed'),
        PackingOrder(order_number='PKG-2026-0202', work_order_id=4, product_name='PCB 主板模組 A', quantity=2000, box_type='L', weight_kg=380.0, operator='Liu Jian-Guo', status='completed'),
        PackingOrder(order_number='PKG-2026-0203', work_order_id=1, product_name='PCB 主板模組 A', quantity=850, box_type='L', weight_kg=162.0, operator='Liu Jian-Guo', status='in_progress'),
    ]
    for item in items:
        s.add(item)


def _seed_shipments(s: Session):
    items = [
        Shipment(shipment_number='SHP-2026-0301', sales_order_id=4, destination='新北市土城區', carrier='新竹物流', eta='2026-03-20', cost=3500, weight_kg=380.0, status='delivered'),
        Shipment(shipment_number='SHP-2026-0302', sales_order_id=2, destination='新竹科學園區', carrier='黑貓宅急便', eta='2026-03-28', cost=2800, weight_kg=125.0, status='in_transit'),
        Shipment(shipment_number='SHP-2026-0303', sales_order_id=1, destination='新竹科學園區', carrier='新竹物流', eta='2026-03-25', cost=3200, weight_kg=162.0, status='pending'),
        Shipment(shipment_number='SHP-2026-0304', sales_order_id=5, destination='台北市內湖區', carrier='順豐速運', eta='2026-03-30', cost=2500, weight_kg=95.0, status='pending'),
        Shipment(shipment_number='SHP-2026-0305', sales_order_id=6, destination='新竹科學園區', carrier='新竹物流', eta='2026-03-15', cost=4200, weight_kg=220.0, status='delivered'),
        Shipment(shipment_number='SHP-2026-0306', sales_order_id=7, destination='新竹科學園區', carrier='黑貓宅急便', eta='2026-03-18', cost=3100, weight_kg=180.0, status='delivered'),
        Shipment(shipment_number='SHP-2026-0307', sales_order_id=8, destination='高雄楠梓加工區', carrier='新竹物流', eta='2026-03-20', cost=3800, weight_kg=145.0, status='delivered'),
        Shipment(shipment_number='SHP-2026-0308', sales_order_id=9, destination='新北市土城區', carrier='順豐速運', eta='2026-03-10', cost=5500, weight_kg=520.0, status='delivered'),
        Shipment(shipment_number='SHP-2026-0309', sales_order_id=12, destination='高雄楠梓加工區', carrier='新竹物流', eta='2026-03-08', cost=2800, weight_kg=130.0, status='delivered'),
    ]
    for item in items:
        s.add(item)


def _seed_service_tickets(s: Session):
    items = [
        ServiceTicket(ticket_number='TKT-2026-0401', customer_id=4, customer_name='鴻海精密', issue='PCB 模組批次 WO-0004 有 3 件功能異常', priority='P1', sla_hours=4, assigned_to='Wu Jia-Rong', status='in_progress'),
        ServiceTicket(ticket_number='TKT-2026-0402', customer_id=2, customer_name='聯華電子', issue='感測器套件包裝破損', priority='P3', sla_hours=24, assigned_to='Wu Jia-Rong', status='open'),
        ServiceTicket(ticket_number='TKT-2026-0403', customer_id=1, customer_name='台灣積體電路', issue='詢問交期變更可能', priority='P2', sla_hours=8, assigned_to='Wu Jia-Rong', status='closed', resolved_at='2026-03-16 15:30'),
    ]
    for item in items:
        s.add(item)
