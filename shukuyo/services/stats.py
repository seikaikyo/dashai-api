"""使用統計服務"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlmodel import Session, select
from shukuyo.models.stats import UsageStats, Features


class StatsService:
    """使用統計服務"""

    def log_usage(self, session: Optional[Session], feature: str) -> None:
        """記錄功能使用次數（使用傳入的 session，fallback 到獨立 session）"""
        try:
            if session is not None:
                self._do_log(session, feature)
                return

            from database import engine
            if engine is None:
                return
            with Session(engine) as stats_session:
                self._do_log(stats_session, feature)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("[Stats] 記錄失敗: %s", e)

    def _do_log(self, session: Session, feature: str) -> None:
        """實際記錄邏輯"""
        today = date.today()
        stats = session.exec(
            select(UsageStats)
            .where(UsageStats.feature == feature)
            .where(UsageStats.stat_date == today)
        ).first()

        if stats:
            stats.count += 1
            stats.updated_at = datetime.now(timezone.utc)
        else:
            stats = UsageStats(feature=feature, stat_date=today, count=1)
            session.add(stats)
        session.commit()

    def get_daily_stats(
        self,
        session: Session,
        feature: Optional[str] = None,
        days: int = 7
    ) -> list[dict]:
        """取得每日統計資料"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        query = select(UsageStats).where(
            UsageStats.stat_date >= start_date,
            UsageStats.stat_date <= end_date
        )

        if feature:
            query = query.where(UsageStats.feature == feature)

        query = query.order_by(UsageStats.stat_date.desc(), UsageStats.feature)
        results = session.exec(query).all()

        return [
            {
                "feature": r.feature,
                "date": r.stat_date.isoformat(),
                "count": r.count
            }
            for r in results
        ]

    def get_summary(self, session: Session, days: int = 30) -> dict:
        """取得統計摘要"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        results = session.exec(
            select(UsageStats).where(
                UsageStats.stat_date >= start_date,
                UsageStats.stat_date <= end_date
            )
        ).all()

        # 依功能彙總
        summary = {}
        total = 0

        for r in results:
            if r.feature not in summary:
                summary[r.feature] = 0
            summary[r.feature] += r.count
            total += r.count

        # 今日統計
        today_results = session.exec(
            select(UsageStats).where(UsageStats.stat_date == end_date)
        ).all()

        today_total = sum(r.count for r in today_results)
        today_by_feature = {r.feature: r.count for r in today_results}

        return {
            "period_days": days,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_usage": total,
            "by_feature": summary,
            "today": {
                "total": today_total,
                "by_feature": today_by_feature
            }
        }


# 全域實例
stats_service = StatsService()
