"""AI Tool definitions and execution for function calling."""

from datetime import datetime
from sqlmodel import Session, select, func
from factory.models.order import SalesOrder
from factory.models.production import WorkOrder
from factory.models.quality import NcrRecord
from factory.models.master import Equipment
from factory.models.shipping import Shipment
from factory.models.service import ServiceTicket
from factory.models.planning import ProductionSchedule
from factory.models.packing import PackingOrder


# -- OpenAI-format tool definitions --

TOOLS = [
    # ==================== READ ====================
    {
        'type': 'function',
        'function': {
            'name': 'query_orders',
            'description': 'Query sales orders. Filter by customer name, status, or date range.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'customer_name': {
                        'type': 'string',
                        'description': 'Customer name to search (partial match)',
                    },
                    'status': {
                        'type': 'string',
                        'description': 'Order status filter',
                        'enum': ['draft', 'confirmed', 'in_production', 'shipped', 'delivered', 'cancelled'],
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Max results (default 20)',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'query_work_orders',
            'description': 'Query production work orders. Filter by product, status, or production line.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'product_name': {
                        'type': 'string',
                        'description': 'Product name to search (partial match)',
                    },
                    'status': {
                        'type': 'string',
                        'description': 'Work order status',
                        'enum': ['created', 'in_progress', 'completed', 'cancelled'],
                    },
                    'line': {
                        'type': 'string',
                        'description': 'Production line name',
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Max results (default 20)',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_dashboard_kpis',
            'description': 'Get real-time factory KPIs: OTD rate, capacity utilization, yield rate, revenue, order/production/quality/shipping/service stats.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'trace_order',
            'description': 'Trace a sales order through the entire supply chain: order -> planning -> production -> quality -> packing -> shipping -> service.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'so_id': {
                        'type': 'integer',
                        'description': 'Sales order ID',
                    },
                    'so_number': {
                        'type': 'string',
                        'description': 'Sales order number (e.g. SO-2026-0001). Use this if user mentions an order number instead of ID.',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_quality_issues',
            'description': 'Search NCR (Non-Conformance Report) quality issues. Filter by severity, status, or defect type.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'severity': {
                        'type': 'string',
                        'description': 'Issue severity',
                        'enum': ['minor', 'major', 'critical'],
                    },
                    'status': {
                        'type': 'string',
                        'description': 'Issue status',
                        'enum': ['open', 'investigating', 'corrective_action', 'closed'],
                    },
                    'defect_type': {
                        'type': 'string',
                        'description': 'Defect type to search (partial match)',
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Max results (default 20)',
                    },
                },
            },
        },
    },
    # ==================== WRITE ====================
    {
        'type': 'function',
        'function': {
            'name': 'update_order_status',
            'description': 'Update a sales order status and/or priority. Use for confirming, shipping, cancelling orders, or marking as urgent.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'so_id': {
                        'type': 'integer',
                        'description': 'Sales order ID',
                    },
                    'so_number': {
                        'type': 'string',
                        'description': 'Sales order number (e.g. SO-2026-0001)',
                    },
                    'status': {
                        'type': 'string',
                        'description': 'New status',
                        'enum': ['draft', 'confirmed', 'in_production', 'shipped', 'delivered', 'cancelled'],
                    },
                    'note': {
                        'type': 'string',
                        'description': 'Reason or note for the status change',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'create_work_order',
            'description': 'Create a new production work order. Links to a sales order. Assigns to a production line.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'sales_order_id': {
                        'type': 'integer',
                        'description': 'Sales order ID to link this work order to',
                    },
                    'product_name': {
                        'type': 'string',
                        'description': 'Product to produce',
                    },
                    'quantity': {
                        'type': 'integer',
                        'description': 'Quantity to produce',
                    },
                    'line': {
                        'type': 'string',
                        'description': 'Production line assignment (e.g. Line 1, Line 2)',
                    },
                    'priority': {
                        'type': 'string',
                        'description': 'Priority level',
                        'enum': ['low', 'normal', 'high', 'urgent'],
                    },
                },
                'required': ['product_name', 'quantity', 'line'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'update_work_order',
            'description': 'Update a work order: change status, update progress (completed/scrap qty), reassign line, or change priority. Use for pausing, resuming, completing work orders, or reporting production progress.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'wo_id': {
                        'type': 'integer',
                        'description': 'Work order ID',
                    },
                    'wo_number': {
                        'type': 'string',
                        'description': 'Work order number (e.g. WO-2026-0001)',
                    },
                    'status': {
                        'type': 'string',
                        'description': 'New status',
                        'enum': ['created', 'in_progress', 'completed', 'cancelled'],
                    },
                    'completed_qty': {
                        'type': 'integer',
                        'description': 'Completed quantity (cumulative)',
                    },
                    'scrap_qty': {
                        'type': 'integer',
                        'description': 'Scrap quantity (cumulative)',
                    },
                    'line': {
                        'type': 'string',
                        'description': 'Reassign to different production line',
                    },
                    'priority': {
                        'type': 'string',
                        'description': 'New priority',
                        'enum': ['low', 'normal', 'high', 'urgent'],
                    },
                    'note': {
                        'type': 'string',
                        'description': 'Reason for update',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'create_quality_issue',
            'description': 'Create a new NCR (Non-Conformance Report). Use when a quality problem is discovered on a production line or in inspection.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'work_order_id': {
                        'type': 'integer',
                        'description': 'Related work order ID',
                    },
                    'product_name': {
                        'type': 'string',
                        'description': 'Affected product',
                    },
                    'defect_type': {
                        'type': 'string',
                        'description': 'Type of defect (e.g. solder bridge, dimension out of spec)',
                    },
                    'severity': {
                        'type': 'string',
                        'description': 'Issue severity',
                        'enum': ['minor', 'major', 'critical'],
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Detailed description of the issue',
                    },
                },
                'required': ['defect_type', 'severity', 'description'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'close_quality_issue',
            'description': 'Close an NCR with root cause and corrective action. Use when a quality investigation is complete.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'ncr_id': {
                        'type': 'integer',
                        'description': 'NCR record ID',
                    },
                    'ncr_number': {
                        'type': 'string',
                        'description': 'NCR number (e.g. NCR-2026-0001)',
                    },
                    'root_cause': {
                        'type': 'string',
                        'description': 'Root cause of the defect',
                    },
                    'corrective_action': {
                        'type': 'string',
                        'description': 'Corrective action taken',
                    },
                },
                'required': ['root_cause', 'corrective_action'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'create_shipment',
            'description': 'Create a shipment for a sales order. Use when order is ready to ship.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'sales_order_id': {
                        'type': 'integer',
                        'description': 'Sales order ID',
                    },
                    'destination': {
                        'type': 'string',
                        'description': 'Shipping destination address',
                    },
                    'carrier': {
                        'type': 'string',
                        'description': 'Shipping carrier (e.g. DHL, FedEx, SF Express)',
                    },
                    'note': {
                        'type': 'string',
                        'description': 'Shipping notes (e.g. fragile, expedited)',
                    },
                },
                'required': ['sales_order_id', 'destination'],
            },
        },
    },
    # ==================== ANALYSIS ====================
    {
        'type': 'function',
        'function': {
            'name': 'analyze_impact',
            'description': 'Analyze the cascading impact of cancelling or delaying a sales order. Traces all downstream: work orders, materials consumed, shipments, NCRs, revenue impact, and KPI changes. Use when user asks "what if" or "what happens if".',
            'parameters': {
                'type': 'object',
                'properties': {
                    'so_id': {
                        'type': 'integer',
                        'description': 'Sales order ID',
                    },
                    'so_number': {
                        'type': 'string',
                        'description': 'Sales order number',
                    },
                    'action': {
                        'type': 'string',
                        'description': 'Proposed action to analyze',
                        'enum': ['cancel', 'delay', 'expedite'],
                    },
                },
                'required': ['action'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'smart_schedule',
            'description': 'Analyze all pending/confirmed orders and current production line load, then propose an optimal production schedule. Shows line utilization, recommended assignments, and projected completion. Use when user asks to schedule, plan, or optimize production.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'execute': {
                        'type': 'boolean',
                        'description': 'If true, actually create the work orders. If false (default), just propose the plan.',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'factory_briefing',
            'description': 'Generate a comprehensive factory status briefing: KPIs, alerts (overdue orders, open critical NCRs, unscheduled orders), and recommended actions. Use at the start of conversation or when user asks for overall status.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'reset_demo',
            'description': 'Reset all factory data back to initial demo state. Use when user says "reset", "start over", or wants a clean demo. WARNING: This deletes all changes.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'confirm': {
                        'type': 'boolean',
                        'description': 'Must be true to execute. Ask user for confirmation first.',
                    },
                },
                'required': ['confirm'],
            },
        },
    },
]


def _to_dict(obj):
    """Convert SQLModel object to dict."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def execute_tool(name: str, args: dict, session: Session) -> dict:
    """Execute a tool and return the result."""
    handlers = {
        'query_orders': lambda: _query_orders(session, **args),
        'query_work_orders': lambda: _query_work_orders(session, **args),
        'get_dashboard_kpis': lambda: _get_dashboard_kpis(session),
        'trace_order': lambda: _trace_order(session, **args),
        'search_quality_issues': lambda: _search_quality_issues(session, **args),
        'update_order_status': lambda: _update_order_status(session, **args),
        'create_work_order': lambda: _create_work_order(session, **args),
        'update_work_order': lambda: _update_work_order(session, **args),
        'create_quality_issue': lambda: _create_quality_issue(session, **args),
        'close_quality_issue': lambda: _close_quality_issue(session, **args),
        'create_shipment': lambda: _create_shipment(session, **args),
        'analyze_impact': lambda: _analyze_impact(session, **args),
        'smart_schedule': lambda: _smart_schedule(session, **args),
        'factory_briefing': lambda: _factory_briefing(session),
        'reset_demo': lambda: _reset_demo(session, **args),
    }
    handler = handlers.get(name)
    if handler:
        return handler()
    return {'error': f'Unknown tool: {name}'}


# ==================== READ TOOLS ====================

def _query_orders(
    session: Session,
    customer_name: str = '',
    status: str = '',
    limit: int = 20,
) -> dict:
    query = select(SalesOrder)
    if customer_name:
        query = query.where(SalesOrder.customer_name.ilike(f'%{customer_name}%'))  # type: ignore
    if status:
        query = query.where(SalesOrder.status == status)
    items = session.exec(query.limit(min(limit, 50))).all()
    total_amount = sum(o.total_amount for o in items)
    return {
        'count': len(items),
        'total_amount': total_amount,
        'orders': [_to_dict(o) for o in items],
    }


def _query_work_orders(
    session: Session,
    product_name: str = '',
    status: str = '',
    line: str = '',
    limit: int = 20,
) -> dict:
    query = select(WorkOrder)
    if product_name:
        query = query.where(WorkOrder.product_name.ilike(f'%{product_name}%'))  # type: ignore
    if status:
        query = query.where(WorkOrder.status == status)
    if line:
        query = query.where(WorkOrder.line.ilike(f'%{line}%'))  # type: ignore
    items = session.exec(query.limit(min(limit, 50))).all()
    return {
        'count': len(items),
        'work_orders': [_to_dict(wo) for wo in items],
    }


def _get_dashboard_kpis(session: Session) -> dict:
    so_rows = session.exec(select(
        func.count().label('total'),
        func.sum(SalesOrder.total_amount).label('revenue'),
        func.count().filter(SalesOrder.status == 'shipped').label('shipped'),
        func.count().filter(SalesOrder.status == 'confirmed').label('confirmed'),
        func.count().filter(SalesOrder.status == 'in_production').label('in_production'),
    ).select_from(SalesOrder)).one()

    so_total = so_rows[0] or 0
    revenue = so_rows[1] or 0
    shipped = so_rows[2] or 0

    wo_rows = session.exec(select(
        func.count().label('total'),
        func.sum(WorkOrder.quantity).label('total_qty'),
        func.sum(WorkOrder.completed_qty).label('completed_qty'),
        func.sum(WorkOrder.scrap_qty).label('scrap_qty'),
        func.count().filter(WorkOrder.status == 'in_progress').label('active'),
    ).select_from(WorkOrder)).one()

    total_qty = wo_rows[1] or 0
    completed_qty = wo_rows[2] or 0
    scrap_qty = wo_rows[3] or 0

    yield_rate = ((completed_qty - scrap_qty) / completed_qty * 100) if completed_qty > 0 else 0
    capacity = (completed_qty / total_qty * 100) if total_qty > 0 else 0
    otd = (shipped / so_total * 100) if so_total > 0 else 0

    ncr_rows = session.exec(select(
        func.count().label('total'),
        func.count().filter(NcrRecord.status != 'closed').label('open'),
        func.count().filter(NcrRecord.severity == 'critical').label('critical'),
    ).select_from(NcrRecord)).one()

    return {
        'otd': round(otd, 1),
        'capacity': round(capacity, 1),
        'yield_rate': round(yield_rate, 2),
        'revenue': round(revenue, 0),
        'orders_total': so_total,
        'orders_shipped': shipped,
        'orders_confirmed': so_rows[3] or 0,
        'orders_in_production': so_rows[4] or 0,
        'wo_total': wo_rows[0] or 0,
        'wo_active': wo_rows[4] or 0,
        'ncr_total': ncr_rows[0] or 0,
        'ncr_open': ncr_rows[1] or 0,
        'ncr_critical': ncr_rows[2] or 0,
    }


def _trace_order(
    session: Session,
    so_id: int = 0,
    so_number: str = '',
) -> dict:
    order = None
    if so_id:
        order = session.get(SalesOrder, so_id)
    elif so_number:
        order = session.exec(
            select(SalesOrder).where(SalesOrder.so_number.ilike(f'%{so_number}%'))  # type: ignore
        ).first()

    if not order:
        return {'error': 'Order not found', 'so_id': so_id, 'so_number': so_number}

    oid = order.id
    schedules = session.exec(
        select(ProductionSchedule).where(ProductionSchedule.sales_order_id == oid)
    ).all()
    work_orders = session.exec(
        select(WorkOrder).where(WorkOrder.sales_order_id == oid)
    ).all()
    wo_ids = [wo.id for wo in work_orders if wo.id]

    ncrs = []
    packings = []
    if wo_ids:
        ncrs = session.exec(
            select(NcrRecord).where(NcrRecord.work_order_id.in_(wo_ids))  # type: ignore
        ).all()
        packings = session.exec(
            select(PackingOrder).where(PackingOrder.work_order_id.in_(wo_ids))  # type: ignore
        ).all()

    shipments = session.exec(
        select(Shipment).where(Shipment.sales_order_id == oid)
    ).all()
    tickets = session.exec(
        select(ServiceTicket).where(ServiceTicket.customer_id == order.customer_id)
    ).all()

    return {
        'order': _to_dict(order),
        'stages': {
            'planning': [_to_dict(s) for s in schedules],
            'production': [_to_dict(wo) for wo in work_orders],
            'quality': [_to_dict(n) for n in ncrs],
            'packing': [_to_dict(p) for p in packings],
            'shipping': [_to_dict(s) for s in shipments],
            'service': [_to_dict(t) for t in tickets],
        },
        'summary': {
            'planning_count': len(schedules),
            'wo_count': len(work_orders),
            'ncr_count': len(ncrs),
            'ncr_open': sum(1 for n in ncrs if n.status != 'closed'),
            'packing_count': len(packings),
            'shipment_count': len(shipments),
            'ticket_count': len(tickets),
        },
    }


def _search_quality_issues(
    session: Session,
    severity: str = '',
    status: str = '',
    defect_type: str = '',
    limit: int = 20,
) -> dict:
    query = select(NcrRecord)
    if severity:
        query = query.where(NcrRecord.severity == severity)
    if status:
        query = query.where(NcrRecord.status == status)
    if defect_type:
        query = query.where(NcrRecord.defect_type.ilike(f'%{defect_type}%'))  # type: ignore
    items = session.exec(query.limit(min(limit, 50))).all()
    return {
        'count': len(items),
        'issues': [_to_dict(n) for n in items],
    }


# ==================== WRITE TOOLS ====================

def _find_order(session: Session, so_id: int = 0, so_number: str = '') -> SalesOrder | None:
    if so_id:
        return session.get(SalesOrder, so_id)
    if so_number:
        return session.exec(
            select(SalesOrder).where(SalesOrder.so_number.ilike(f'%{so_number}%'))  # type: ignore
        ).first()
    return None


def _update_order_status(
    session: Session,
    so_id: int = 0,
    so_number: str = '',
    status: str = '',
    note: str = '',
) -> dict:
    order = _find_order(session, so_id, so_number)
    if not order:
        return {'error': 'Order not found', 'so_id': so_id, 'so_number': so_number}

    old_status = order.status
    if status:
        order.status = status
    if note:
        order.note = f'{order.note}\n[AI] {note}'.strip()
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)

    return {
        'action': 'update_order_status',
        'so_number': order.so_number,
        'old_status': old_status,
        'new_status': order.status,
        'order': _to_dict(order),
    }


def _create_work_order(
    session: Session,
    product_name: str = '',
    quantity: int = 0,
    line: str = '',
    priority: str = 'normal',
    sales_order_id: int | None = None,
) -> dict:
    # Auto-generate WO number
    count = session.exec(select(func.count()).select_from(WorkOrder)).one() or 0
    wo_number = f'WO-2026-{count + 1:04d}'

    wo = WorkOrder(
        wo_number=wo_number,
        product_name=product_name,
        quantity=quantity,
        completed_qty=0,
        scrap_qty=0,
        line=line,
        priority=priority,
        status='created',
        sales_order_id=sales_order_id,
        planned_start=datetime.utcnow().strftime('%Y-%m-%d'),
        note=f'[AI] Created by AI Assistant',
    )
    session.add(wo)
    session.commit()
    session.refresh(wo)

    return {
        'action': 'create_work_order',
        'wo_number': wo.wo_number,
        'product_name': product_name,
        'quantity': quantity,
        'line': line,
        'priority': priority,
        'work_order': _to_dict(wo),
    }


def _update_work_order(
    session: Session,
    wo_id: int = 0,
    wo_number: str = '',
    status: str = '',
    completed_qty: int | None = None,
    scrap_qty: int | None = None,
    line: str = '',
    priority: str = '',
    note: str = '',
) -> dict:
    wo = None
    if wo_id:
        wo = session.get(WorkOrder, wo_id)
    elif wo_number:
        wo = session.exec(
            select(WorkOrder).where(WorkOrder.wo_number.ilike(f'%{wo_number}%'))  # type: ignore
        ).first()

    if not wo:
        return {'error': 'Work order not found', 'wo_id': wo_id, 'wo_number': wo_number}

    changes = {}
    if status:
        changes['status'] = {'old': wo.status, 'new': status}
        wo.status = status
    if completed_qty is not None:
        changes['completed_qty'] = {'old': wo.completed_qty, 'new': completed_qty}
        wo.completed_qty = completed_qty
    if scrap_qty is not None:
        changes['scrap_qty'] = {'old': wo.scrap_qty, 'new': scrap_qty}
        wo.scrap_qty = scrap_qty
    if line:
        changes['line'] = {'old': wo.line, 'new': line}
        wo.line = line
    if priority:
        changes['priority'] = {'old': wo.priority, 'new': priority}
        wo.priority = priority
    if note:
        wo.note = f'{wo.note}\n[AI] {note}'.strip()

    wo.updated_at = datetime.utcnow()
    session.add(wo)
    session.commit()
    session.refresh(wo)

    return {
        'action': 'update_work_order',
        'wo_number': wo.wo_number,
        'changes': changes,
        'work_order': _to_dict(wo),
    }


def _create_quality_issue(
    session: Session,
    defect_type: str = '',
    severity: str = 'major',
    description: str = '',
    work_order_id: int | None = None,
    product_name: str = '',
) -> dict:
    count = session.exec(select(func.count()).select_from(NcrRecord)).one() or 0
    ncr_number = f'NCR-2026-{count + 1:04d}'

    ncr = NcrRecord(
        ncr_number=ncr_number,
        work_order_id=work_order_id,
        product_name=product_name,
        defect_type=defect_type,
        severity=severity,
        status='open',
        description=description,
        detected_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
        note=f'[AI] Created by AI Assistant',
    )
    session.add(ncr)
    session.commit()
    session.refresh(ncr)

    return {
        'action': 'create_quality_issue',
        'ncr_number': ncr.ncr_number,
        'severity': severity,
        'defect_type': defect_type,
        'issue': _to_dict(ncr),
    }


def _close_quality_issue(
    session: Session,
    ncr_id: int = 0,
    ncr_number: str = '',
    root_cause: str = '',
    corrective_action: str = '',
) -> dict:
    ncr = None
    if ncr_id:
        ncr = session.get(NcrRecord, ncr_id)
    elif ncr_number:
        ncr = session.exec(
            select(NcrRecord).where(NcrRecord.ncr_number.ilike(f'%{ncr_number}%'))  # type: ignore
        ).first()

    if not ncr:
        return {'error': 'NCR not found', 'ncr_id': ncr_id, 'ncr_number': ncr_number}

    old_status = ncr.status
    ncr.status = 'closed'
    ncr.root_cause = root_cause
    ncr.corrective_action = corrective_action
    ncr.closed_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    ncr.updated_at = datetime.utcnow()
    session.add(ncr)
    session.commit()
    session.refresh(ncr)

    return {
        'action': 'close_quality_issue',
        'ncr_number': ncr.ncr_number,
        'old_status': old_status,
        'root_cause': root_cause,
        'corrective_action': corrective_action,
        'issue': _to_dict(ncr),
    }


def _create_shipment(
    session: Session,
    sales_order_id: int = 0,
    destination: str = '',
    carrier: str = 'SF Express',
    note: str = '',
) -> dict:
    order = session.get(SalesOrder, sales_order_id)
    if not order:
        return {'error': 'Sales order not found', 'sales_order_id': sales_order_id}

    count = session.exec(select(func.count()).select_from(Shipment)).one() or 0
    ship_number = f'SHP-2026-{count + 1:04d}'

    shipment = Shipment(
        shipment_number=ship_number,
        sales_order_id=sales_order_id,
        destination=destination or order.shipping_address,
        carrier=carrier,
        status='pending',
        eta=datetime.utcnow().strftime('%Y-%m-%d'),
        note=f'[AI] {note}'.strip() if note else '[AI] Created by AI Assistant',
    )
    session.add(shipment)

    # Also update order status to shipped
    order.status = 'shipped'
    order.updated_at = datetime.utcnow()
    session.add(order)

    session.commit()
    session.refresh(shipment)

    return {
        'action': 'create_shipment',
        'shipment_number': ship_number,
        'sales_order': order.so_number,
        'destination': shipment.destination,
        'carrier': carrier,
        'order_status_updated': 'shipped',
        'shipment': _to_dict(shipment),
    }


# ==================== ANALYSIS TOOLS ====================

def _analyze_impact(
    session: Session,
    action: str = 'cancel',
    so_id: int = 0,
    so_number: str = '',
) -> dict:
    order = _find_order(session, so_id, so_number)
    if not order:
        return {'error': 'Order not found', 'so_id': so_id, 'so_number': so_number}

    oid = order.id
    # Trace all downstream
    work_orders = session.exec(
        select(WorkOrder).where(WorkOrder.sales_order_id == oid)
    ).all()
    wo_ids = [wo.id for wo in work_orders if wo.id]

    ncrs = []
    packings = []
    if wo_ids:
        ncrs = session.exec(
            select(NcrRecord).where(NcrRecord.work_order_id.in_(wo_ids))  # type: ignore
        ).all()
        packings = session.exec(
            select(PackingOrder).where(PackingOrder.work_order_id.in_(wo_ids))  # type: ignore
        ).all()

    shipments = session.exec(
        select(Shipment).where(Shipment.sales_order_id == oid)
    ).all()

    # Calculate material/production sunk cost
    total_completed = sum(wo.completed_qty for wo in work_orders)
    total_scrap = sum(wo.scrap_qty for wo in work_orders)
    total_planned = sum(wo.quantity for wo in work_orders)
    sunk_cost_estimate = total_completed * 45  # avg cost per unit

    # KPI impact simulation
    all_orders = session.exec(select(
        func.count(),
        func.count().filter(SalesOrder.status == 'shipped'),
        func.sum(SalesOrder.total_amount),
    ).select_from(SalesOrder)).one()
    current_otd = (all_orders[1] / all_orders[0] * 100) if all_orders[0] else 0
    current_revenue = all_orders[2] or 0

    if action == 'cancel':
        new_total = (all_orders[0] or 0) - 1
        new_otd = (all_orders[1] / new_total * 100) if new_total else 0
        revenue_loss = order.total_amount
        recommendation = 'Consider delaying instead of cancelling to preserve sunk cost'
    elif action == 'delay':
        new_otd = current_otd  # OTD unchanged until delivery date passes
        revenue_loss = 0
        recommendation = 'Delay preserves investment but may affect customer relationship'
    else:  # expedite
        new_otd = current_otd
        revenue_loss = 0
        recommendation = 'Expediting may require overtime or line reallocation'

    return {
        'action': f'impact_analysis_{action}',
        'order': {
            'so_number': order.so_number,
            'customer': order.customer_name,
            'amount': order.total_amount,
            'status': order.status,
        },
        'downstream': {
            'work_orders': len(work_orders),
            'work_orders_detail': [
                {'wo_number': wo.wo_number, 'status': wo.status,
                 'completed': wo.completed_qty, 'planned': wo.quantity, 'line': wo.line}
                for wo in work_orders
            ],
            'ncrs': len(ncrs),
            'ncrs_open': sum(1 for n in ncrs if n.status != 'closed'),
            'packings': len(packings),
            'shipments': len(shipments),
        },
        'financial_impact': {
            'order_amount': order.total_amount,
            'sunk_cost_estimate': sunk_cost_estimate,
            'units_completed': total_completed,
            'units_scrapped': total_scrap,
            'units_remaining': max(total_planned - total_completed, 0),
            'revenue_loss': revenue_loss,
        },
        'kpi_impact': {
            'current_otd': round(current_otd, 1),
            'projected_otd': round(new_otd, 1),
            'current_revenue': current_revenue,
            'projected_revenue': current_revenue - revenue_loss,
        },
        'recommendation': recommendation,
    }


def _smart_schedule(
    session: Session,
    execute: bool = False,
) -> dict:
    # Get orders needing production (confirmed but no WO, or with incomplete WOs)
    confirmed_orders = session.exec(
        select(SalesOrder).where(SalesOrder.status.in_(['confirmed', 'in_production']))  # type: ignore
    ).all()

    # Get current line utilization
    active_wos = session.exec(
        select(WorkOrder).where(WorkOrder.status.in_(['created', 'in_progress']))  # type: ignore
    ).all()

    lines = ['Line 1', 'Line 2', 'Line 3', 'Line 4', 'Line 5']
    line_load: dict[str, int] = {line: 0 for line in lines}
    line_wos: dict[str, list[str]] = {line: [] for line in lines}
    for wo in active_wos:
        if wo.line in line_load:
            line_load[wo.line] += wo.quantity - wo.completed_qty
            line_wos[wo.line].append(wo.wo_number)

    max_capacity_per_line = 2000  # units per week estimate
    line_util = {
        line: round(load / max_capacity_per_line * 100, 1)
        for line, load in line_load.items()
    }

    # Find orders without WOs
    orders_needing_wo = []
    for so in confirmed_orders:
        existing_wos = session.exec(
            select(WorkOrder).where(WorkOrder.sales_order_id == so.id)
        ).all()
        total_wo_qty = sum(wo.quantity for wo in existing_wos)
        # Estimate order quantity from amount (rough: amount / avg unit cost)
        est_qty = max(int(so.total_amount / 50), 100)
        if total_wo_qty < est_qty:
            orders_needing_wo.append({
                'so_id': so.id,
                'so_number': so.so_number,
                'customer': so.customer_name,
                'amount': so.total_amount,
                'delivery_date': so.delivery_date,
                'estimated_qty': est_qty - total_wo_qty,
                'existing_wo_qty': total_wo_qty,
            })

    # Propose schedule: assign to least loaded lines
    schedule_plan = []
    sorted_lines = sorted(line_util.items(), key=lambda x: x[1])

    for i, order_info in enumerate(orders_needing_wo):
        target_line = sorted_lines[i % len(sorted_lines)][0]
        schedule_plan.append({
            'so_number': order_info['so_number'],
            'customer': order_info['customer'],
            'quantity': order_info['estimated_qty'],
            'assigned_line': target_line,
            'delivery_date': order_info['delivery_date'],
            'priority': 'high' if order_info['delivery_date'] and order_info['delivery_date'] < datetime.utcnow().strftime('%Y-%m-%d') else 'normal',
        })

    created_wos = []
    if execute and schedule_plan:
        for plan in schedule_plan:
            so = session.exec(
                select(SalesOrder).where(SalesOrder.so_number == plan['so_number'])
            ).first()
            if so:
                result = _create_work_order(
                    session,
                    product_name=f'Order {plan["so_number"]}',
                    quantity=plan['quantity'],
                    line=plan['assigned_line'],
                    priority=plan['priority'],
                    sales_order_id=so.id,
                )
                created_wos.append(result.get('wo_number', ''))
                # Update order status
                so.status = 'in_production'
                so.updated_at = datetime.utcnow()
                session.add(so)
        session.commit()

    return {
        'action': 'smart_schedule',
        'executed': execute,
        'line_utilization': line_util,
        'line_active_wos': {k: len(v) for k, v in line_wos.items()},
        'orders_needing_scheduling': len(orders_needing_wo),
        'proposed_schedule': schedule_plan,
        'created_work_orders': created_wos if execute else [],
        'summary': {
            'total_orders': len(orders_needing_wo),
            'total_quantity': sum(p['quantity'] for p in schedule_plan),
            'lines_used': list(set(p['assigned_line'] for p in schedule_plan)),
        },
    }


def _factory_briefing(session: Session, lang: str = 'zh-TW') -> dict:
    kpis = _get_dashboard_kpis(session)

    # i18n text templates
    T = {
        'zh-TW': {
            'active_wos': '{n} 張進行中工單在 {line}',
            'unknown_line': '未知產線',
            'ncr_opt1_label': '立即停線 + 調查',
            'ncr_opt1_impact': '產線停止，{n} 張工單暫停。最快控制缺陷擴散。',
            'ncr_opt2_label': '降速生產 + 加強抽檢',
            'ncr_opt2_impact': '50% 速度繼續生產。若缺陷持續，預估 {s}+ 件報廢。',
            'ncr_opt3_label': '觀察，下班後處理',
            'ncr_opt3_impact': '不立即處理。{s}+ 件有風險，可能升級為客訴。',
            'delivery': '交期: {date} ({days})',
            'days_left': '剩 {n} 天',
            'days_overdue': '逾期 {n} 天',
            'so_opt1_label': '排入 {line} (利用率 {util}%)',
            'so_opt1_impact': '最佳產線分配。預估 {d} 天完成。',
            'so_opt2_label': '分散到 {line1} + {line2}',
            'so_opt2_impact': '更快完成但協調成本較高。適合大單。',
            'so_opt3_label': '與客戶協商延期',
            'so_opt3_impact': '不影響生產。客戶關係風險。營收 ${amt} 可能受影響。',
            'idle_title': '{n} 條閒置產線: {lines}',
            'idle_context': '運行中產線平均利用率 {avg}%。{p} 張訂單待排程。',
            'idle_opt1_label': '執行智慧排程（自動分配待排訂單）',
            'idle_opt1_impact': '將 {p} 張訂單最佳化分配到可用產線。',
            'idle_opt2_label': '安排閒置產線預防保養',
            'idle_opt2_impact': '利用停機時間做預防保養，降低未來故障風險。',
            'idle_opt3_label': '維持閒置，等待新訂單',
            'idle_opt3_impact': '閒置產能成本約 ${cost}/天。需求低時可接受。',
        },
        'en': {
            'active_wos': '{n} active WOs on {line}',
            'unknown_line': 'unknown line',
            'ncr_opt1_label': 'Immediately pause line + investigate',
            'ncr_opt1_impact': 'Production stops, {n} WOs paused. Fastest to contain defect.',
            'ncr_opt2_label': 'Slow down + increase inspection',
            'ncr_opt2_impact': 'Production at 50% speed. Risk of {s}+ scrap units if defect persists.',
            'ncr_opt3_label': 'Monitor only, handle after shift',
            'ncr_opt3_impact': 'No immediate action. {s}+ units at risk. May escalate to complaint.',
            'delivery': 'Delivery: {date} ({days})',
            'days_left': '{n}d left',
            'days_overdue': '{n}d overdue',
            'so_opt1_label': 'Schedule to {line} (utilization {util}%)',
            'so_opt1_impact': 'Optimal line assignment. Estimated completion: {d} days.',
            'so_opt2_label': 'Split across {line1} + {line2}',
            'so_opt2_impact': 'Faster completion but higher coordination overhead. Good for large orders.',
            'so_opt3_label': 'Negotiate delivery extension',
            'so_opt3_impact': 'No production impact. Customer risk. Revenue ${amt} at stake.',
            'idle_title': '{n} idle lines: {lines}',
            'idle_context': 'Active lines avg {avg}% utilization. {p} orders awaiting schedule.',
            'idle_opt1_label': 'Run smart scheduling (auto-assign)',
            'idle_opt1_impact': 'Distribute {p} orders optimally across available lines.',
            'idle_opt2_label': 'Schedule maintenance on idle lines',
            'idle_opt2_impact': 'Use downtime for preventive maintenance. Reduces breakdown risk.',
            'idle_opt3_label': 'Keep idle, wait for new orders',
            'idle_opt3_impact': 'Lost capacity ~${cost}/day. Acceptable if demand is low.',
        },
        'ja': {
            'active_wos': '{line} に進行中 WO {n} 件',
            'unknown_line': '不明ライン',
            'ncr_opt1_label': '即時ライン停止 + 調査',
            'ncr_opt1_impact': '生産停止、WO {n} 件一時停止。不良拡散防止に最速。',
            'ncr_opt2_label': '減速生産 + 検査頻度UP',
            'ncr_opt2_impact': '50%速度で継続。不良継続時 {s}+ 件スクラップリスク。',
            'ncr_opt3_label': '監視のみ、シフト後対応',
            'ncr_opt3_impact': '即時対応なし。{s}+ 件リスク。クレームに発展の可能性。',
            'delivery': '納期: {date} ({days})',
            'days_left': '残り {n} 日',
            'days_overdue': '{n} 日超過',
            'so_opt1_label': '{line} に投入 (稼働率 {util}%)',
            'so_opt1_impact': '最適ライン割当。完了予定: {d} 日。',
            'so_opt2_label': '{line1} + {line2} に分散',
            'so_opt2_impact': '完了は早いが調整コスト増。大口注文向き。',
            'so_opt3_label': '顧客と納期延長を交渉',
            'so_opt3_impact': '生産影響なし。顧客関係リスク。売上 ${amt} に影響の可能性。',
            'idle_title': '遊休ライン {n} 本: {lines}',
            'idle_context': '稼働中ライン平均 {avg}%。{p} 件の注文がスケジュール待ち。',
            'idle_opt1_label': 'スマートスケジューリング実行',
            'idle_opt1_impact': '{p} 件の注文を最適配分。',
            'idle_opt2_label': '遊休ラインの予防保全を実施',
            'idle_opt2_impact': 'ダウンタイムを活用し予防保全。将来の故障リスク低減。',
            'idle_opt3_label': '遊休維持、新規注文待ち',
            'idle_opt3_impact': '遊休コスト約 ${cost}/日。需要低下時は許容範囲。',
        },
    }
    t = T.get(lang, T['en'])

    alerts = []

    # Line utilization context
    active_wos = session.exec(
        select(WorkOrder).where(WorkOrder.status.in_(['created', 'in_progress']))  # type: ignore
    ).all()
    lines_list = ['Line 1', 'Line 2', 'Line 3', 'Line 4', 'Line 5']
    line_load: dict[str, int] = {line: 0 for line in lines_list}
    for wo in active_wos:
        if wo.line in line_load:
            line_load[wo.line] += wo.quantity - wo.completed_qty
    max_cap = 2000
    line_util = {line: round(load / max_cap * 100, 1) for line, load in line_load.items()}
    sorted_lines = sorted(line_util.items(), key=lambda x: x[1])
    least_busy = sorted_lines[0][0]
    second_busy = sorted_lines[1][0] if len(sorted_lines) > 1 else least_busy
    idle_lines = [l for l, u in line_util.items() if u == 0]

    # 1. Critical/Major open NCRs
    open_ncrs = session.exec(
        select(NcrRecord)
        .where(NcrRecord.severity.in_(['critical', 'major']))  # type: ignore
        .where(NcrRecord.status != 'closed')
    ).all()
    for ncr in open_ncrs:
        related_wo_count = 0
        ncr_line = ''
        if ncr.work_order_id:
            wo = session.get(WorkOrder, ncr.work_order_id)
            if wo:
                ncr_line = wo.line
                related_wo_count = session.exec(
                    select(func.count()).select_from(WorkOrder)
                    .where(WorkOrder.line == wo.line)
                    .where(WorkOrder.status == 'in_progress')
                ).one() or 0

        scrap_risk = related_wo_count * 50
        alerts.append({
            'type': 'critical_ncr',
            'severity': 'high' if ncr.severity == 'critical' else 'medium',
            'title': f'{ncr.ncr_number}: {ncr.defect_type} ({ncr.product_name})',
            'context': t['active_wos'].format(n=related_wo_count, line=ncr_line or t['unknown_line']),
            'options': [
                {
                    'label': t['ncr_opt1_label'],
                    'risk_pct': 15,
                    'impact': t['ncr_opt1_impact'].format(n=related_wo_count),
                    'action_prompt': f'Pause all work orders on {ncr_line} and investigate {ncr.ncr_number}',
                    'recommended': True,
                },
                {
                    'label': t['ncr_opt2_label'],
                    'risk_pct': 55,
                    'impact': t['ncr_opt2_impact'].format(s=scrap_risk),
                    'action_prompt': f'Reduce speed on {ncr_line} and add inspection for {ncr.ncr_number}',
                    'recommended': False,
                },
                {
                    'label': t['ncr_opt3_label'],
                    'risk_pct': 85,
                    'impact': t['ncr_opt3_impact'].format(s=scrap_risk),
                    'action_prompt': f'Mark {ncr.ncr_number} for review after current shift',
                    'recommended': False,
                },
            ],
        })

    # 2. Confirmed orders without work orders
    confirmed = session.exec(
        select(SalesOrder).where(SalesOrder.status == 'confirmed')
    ).all()
    for so in confirmed:
        wo_count = session.exec(
            select(func.count()).select_from(WorkOrder)
            .where(WorkOrder.sales_order_id == so.id)
        ).one() or 0
        if wo_count == 0:
            days_left = 0
            days_text = ''
            if so.delivery_date:
                try:
                    dd = datetime.strptime(so.delivery_date, '%Y-%m-%d')
                    days_left = (dd - datetime.utcnow()).days
                    days_text = t['days_left'].format(n=days_left) if days_left > 0 else t['days_overdue'].format(n=abs(days_left))
                except ValueError:
                    pass

            overdue = days_left <= 0
            alerts.append({
                'type': 'unscheduled_order',
                'severity': 'high' if overdue or days_left <= 3 else 'medium',
                'title': f'{so.so_number}: {so.customer_name} (${so.total_amount:,.0f})',
                'context': t['delivery'].format(date=so.delivery_date, days=days_text),
                'options': [
                    {
                        'label': t['so_opt1_label'].format(line=least_busy, util=line_util[least_busy]),
                        'risk_pct': 10 if days_left > 5 else 25,
                        'impact': t['so_opt1_impact'].format(d=max(days_left - 3, 1)),
                        'action_prompt': f'Create work order for {so.so_number} on {least_busy} with {"urgent" if overdue else "high"} priority',
                        'recommended': True,
                    },
                    {
                        'label': t['so_opt2_label'].format(line1=least_busy, line2=second_busy),
                        'risk_pct': 15,
                        'impact': t['so_opt2_impact'],
                        'action_prompt': f'Split {so.so_number} production across {least_busy} and {second_busy}',
                        'recommended': False,
                    },
                    {
                        'label': t['so_opt3_label'],
                        'risk_pct': 40,
                        'impact': t['so_opt3_impact'].format(amt=f'{so.total_amount:,.0f}'),
                        'action_prompt': f'Delay {so.so_number} and update delivery date',
                        'recommended': False,
                    },
                ],
            })

    # 3. Idle lines
    if idle_lines and len(idle_lines) >= 2:
        util_active = [u for u in line_util.values() if u > 0]
        avg_active = round(sum(util_active) / len(util_active), 1) if util_active else 0
        pending_count = len([so for so in confirmed if session.exec(
            select(func.count()).select_from(WorkOrder)
            .where(WorkOrder.sales_order_id == so.id)
        ).one() == 0])

        alerts.append({
            'type': 'idle_lines',
            'severity': 'low',
            'title': t['idle_title'].format(n=len(idle_lines), lines=', '.join(sorted(idle_lines))),
            'context': t['idle_context'].format(avg=avg_active, p=pending_count),
            'options': [
                {
                    'label': t['idle_opt1_label'],
                    'risk_pct': 5,
                    'impact': t['idle_opt1_impact'].format(p=pending_count),
                    'action_prompt': 'Run smart scheduling to optimize all production lines',
                    'recommended': True,
                },
                {
                    'label': t['idle_opt2_label'],
                    'risk_pct': 10,
                    'impact': t['idle_opt2_impact'],
                    'action_prompt': 'Schedule preventive maintenance on idle lines',
                    'recommended': False,
                },
                {
                    'label': t['idle_opt3_label'],
                    'risk_pct': 20,
                    'impact': t['idle_opt3_impact'].format(cost=f'{len(idle_lines) * 8000:,}'),
                    'action_prompt': 'No action on idle lines, continue monitoring',
                    'recommended': False,
                },
            ],
        })

    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    alerts.sort(key=lambda a: severity_order.get(a.get('severity', 'low'), 3))

    return {
        'action': 'factory_briefing',
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
        'kpis': kpis,
        'line_utilization': line_util,
        'alerts_count': len(alerts),
        'alerts': alerts,
        'summary': {
            'critical_issues': sum(1 for a in alerts if a.get('severity') == 'high'),
            'warnings': sum(1 for a in alerts if a.get('severity') == 'medium'),
            'info': sum(1 for a in alerts if a.get('severity') == 'low'),
        },
    }


def _reset_demo(
    session: Session,
    confirm: bool = False,
) -> dict:
    if not confirm:
        return {
            'action': 'reset_demo',
            'executed': False,
            'message': 'Reset requires confirmation. Set confirm=true to proceed.',
        }

    from sqlmodel import SQLModel
    from database import engine, create_db_and_tables
    from services.seed_data import seed_all

    SQLModel.metadata.drop_all(engine)
    create_db_and_tables()
    with Session(engine) as fresh_session:
        seed_all(fresh_session)

    return {
        'action': 'reset_demo',
        'executed': True,
        'message': 'All data reset to initial demo state.',
    }
