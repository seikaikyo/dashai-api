from fastapi import APIRouter, Query
from typing import Optional, Literal
from starlette.requests import Request
from ..limiter import limiter
from ..services.learning_service import async_get_learning_stats, async_get_weak_areas

router = APIRouter(prefix='/api/progress', tags=['progress'])


@router.get('')
@limiter.limit("60/minute")
async def get_progress(request: Request, level: Optional[Literal['n5', 'n4', 'n3', 'n2', 'n1']] = Query(None)):
    """取得學習進度（可按級別過濾）"""
    stats = await async_get_learning_stats(level=level)
    weak_areas = await async_get_weak_areas(level=level)

    return {
        'success': True,
        'data': {
            'stats': stats,
            'weak_areas': weak_areas
        }
    }


@router.get('/summary')
@limiter.limit("60/minute")
async def get_summary(request: Request, level: Optional[Literal['n5', 'n4', 'n3', 'n2', 'n1']] = Query(None)):
    """取得簡要統計"""
    stats = await async_get_learning_stats(level=level)

    total_correct = sum(d['correct'] for d in stats['by_mode'].values())
    total_count = sum(d['total'] for d in stats['by_mode'].values())

    return {
        'success': True,
        'data': {
            'total_practices': stats['total_practices'],
            'overall_accuracy': total_correct / total_count if total_count > 0 else 0,
            'by_mode': {
                mode: {
                    'count': data['total'],
                    'accuracy': data['accuracy']
                }
                for mode, data in stats['by_mode'].items()
            },
            'weak_grammar_count': len([
                g for g, d in stats['grammar_mastery'].items()
                if d['level'] < 0.6
            ])
        }
    }
