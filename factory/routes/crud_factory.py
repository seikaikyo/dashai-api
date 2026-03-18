from typing import Type, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import SQLModel, Session, select, func
from database import get_session


def generate_crud_router(
    *,
    model: Type[SQLModel],
    create_model: Type[SQLModel],
    update_model: Type[SQLModel],
    prefix: str,
    tags: list[str],
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=tags)

    @router.get('/', response_model=dict)
    def list_items(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        search: Optional[str] = Query(None),
        session: Session = Depends(get_session),
    ):
        offset = (page - 1) * limit
        query = select(model)

        if search:
            from sqlalchemy import or_
            searchable = {'name', 'code', 'customer_name', 'supplier_name',
                          'product_name', 'material_name', 'so_number', 'wo_number',
                          'po_number', 'ncr_number', 'shipment_number', 'ticket_number',
                          'order_number', 'schedule_number', 'txn_number', 'eval_number',
                          'issue', 'defect_type', 'description', 'destination', 'carrier'}
            str_cols = [
                c for c in model.__table__.columns
                if c.name in searchable
            ]
            if str_cols:
                query = query.where(or_(
                    *[col.ilike(f'%{search}%') for col in str_cols]
                ))

        total = session.exec(
            select(func.count()).select_from(query.subquery())
        ).one()
        items = session.exec(query.offset(offset).limit(limit)).all()

        return {
            'success': True,
            'data': items,
            'total': total,
            'page': page,
            'limit': limit,
        }

    @router.get('/{item_id}', response_model=dict)
    def get_item(item_id: int, session: Session = Depends(get_session)):
        item = session.get(model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail='Not found')
        return {'success': True, 'data': item}

    @router.post('/', response_model=dict, status_code=201)
    def create_item(
        body: create_model,  # type: ignore
        session: Session = Depends(get_session),
    ):
        item = model.model_validate(body)
        session.add(item)
        session.commit()
        session.refresh(item)
        return {'success': True, 'data': item}

    @router.patch('/{item_id}', response_model=dict)
    def update_item(
        item_id: int,
        body: update_model,  # type: ignore
        session: Session = Depends(get_session),
    ):
        item = session.get(model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail='Not found')
        update_data = body.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)
        session.add(item)
        session.commit()
        session.refresh(item)
        return {'success': True, 'data': item}

    @router.delete('/{item_id}', response_model=dict)
    def delete_item(item_id: int, session: Session = Depends(get_session)):
        item = session.get(model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail='Not found')
        session.delete(item)
        session.commit()
        return {'success': True, 'data': {'id': item_id}}

    return router
