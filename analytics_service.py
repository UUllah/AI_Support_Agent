from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from log_parser import LogParser, percentile, safe_mean
from ticket_classifier import TicketClassifier


DEFAULT_CATEGORY_ORDER = [
    "Login Issues",
    "Transaction Failures",
    "ATM / Cash Out Issues",
    "Mobile Banking Issues",
    "UAT Setup Requests",
    "DR / Failover Setup",
    "API Integration Issues",
    "Performance / Slow Response",
    "Configuration / Deployment Issues",
    "Other",
]


class AnalyticsService:
    def __init__(self):
        self.ticket_classifier = TicketClassifier()
        self.log_parser = LogParser()
        self._ticket_summary: Optional[Dict[str, Any]] = None
        self._log_summary: Optional[Dict[str, Any]] = None

    def analyze_tickets(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(tickets)
        category_counts = Counter({category: 0 for category in DEFAULT_CATEGORY_ORDER})
        category_ticket_ids = defaultdict(list)
        daily_trend = defaultdict(Counter)
        weekly_trend = defaultdict(Counter)
        enriched_tickets: List[Dict[str, Any]] = []

        for ticket in tickets:
            classified = self.ticket_classifier.classify_ticket(ticket)
            category = classified["category"] if classified["category"] in category_counts else "Other"
            category_counts[category] += 1
            if len(category_ticket_ids[category]) < 5:
                category_ticket_ids[category].append(classified["ticket_id"])

            ticket_date = self._extract_ticket_date(ticket)
            if ticket_date:
                day_key = ticket_date.strftime("%Y-%m-%d")
                week_key = f"{ticket_date.isocalendar().year}-W{ticket_date.isocalendar().week:02d}"
                daily_trend[day_key][category] += 1
                weekly_trend[week_key][category] += 1

            enriched_tickets.append(
                {
                    "ticket_id": classified["ticket_id"],
                    "subject": classified["subject"],
                    "summary": classified["summary"],
                    "category": category,
                    "insight": classified["insight"],
                }
            )

        categories = []
        for category in DEFAULT_CATEGORY_ORDER:
            count = category_counts[category]
            categories.append(
                {
                    "name": category,
                    "count": count,
                    "percentage": round((count / total) * 100, 2) if total else 0.0,
                    "top_ticket_ids": category_ticket_ids[category],
                }
            )

        top_category = max(categories, key=lambda item: item["count"], default={"name": "Other", "count": 0, "percentage": 0})
        top_tickets = sorted(
            enriched_tickets,
            key=lambda item: (category_counts[item["category"]], str(item["ticket_id"])),
            reverse=True,
        )[:10]

        summary = {
            "total_tickets": total,
            "categories": categories,
            "top_recurring_category": top_category,
            "daily_trend": self._format_trend(daily_trend),
            "weekly_trend": self._format_trend(weekly_trend),
            "top_tickets": top_tickets,
        }
        self._ticket_summary = summary
        return summary

    def get_ticket_summary(self) -> Optional[Dict[str, Any]]:
        return self._ticket_summary

    def analyze_log_upload(self, filename: str, content: bytes) -> Dict[str, Any]:
        parsed = self.log_parser.parse_upload(filename, content)
        rows = parsed.pop("parsed_rows")

        total_hits = len(rows)
        minute_counts = Counter(row["minute"] for row in rows if row.get("minute"))
        hour_counts = Counter(row["hour"] for row in rows if row.get("hour") is not None)
        endpoint_counts = Counter(row["endpoint"] for row in rows if row.get("endpoint"))
        response_times = [row["response_time"] for row in rows if row.get("response_time") is not None]
        failed_rows = [row for row in rows if row.get("status") and row["status"] >= 400]
        failed_api_counts = Counter(row["endpoint"] for row in failed_rows if row.get("endpoint"))

        endpoint_timings = defaultdict(list)
        for row in rows:
            if row.get("endpoint") and row.get("response_time") is not None:
                endpoint_timings[row["endpoint"]].append(row["response_time"])

        slow_apis = sorted(
            [
                {
                    "endpoint": endpoint,
                    "average_response_time_ms": safe_mean(values),
                    "hits": len(values),
                }
                for endpoint, values in endpoint_timings.items()
            ],
            key=lambda item: item["average_response_time_ms"],
            reverse=True,
        )[:5]

        peak_hours = self._hour_rank(hour_counts, reverse=True)
        non_peak_hours = self._hour_rank(hour_counts, reverse=False)

        summary = {
            **parsed,
            "metrics": {
                "total_api_hits": total_hits,
                "transactions_per_minute": round(total_hits / max(1, len(minute_counts)), 2) if total_hits else 0.0,
                "requests_per_minute": round(total_hits / max(1, len(minute_counts)), 2) if total_hits else 0.0,
                "peak_hours": peak_hours,
                "non_peak_hours": non_peak_hours,
                "slow_apis": slow_apis,
                "top_endpoints": [
                    {"endpoint": endpoint, "hits": count}
                    for endpoint, count in endpoint_counts.most_common(10)
                ],
                "error_rate_percentage": round((len(failed_rows) / total_hits) * 100, 2) if total_hits else 0.0,
                "status_4xx_count": sum(1 for row in rows if row.get("status") and 400 <= row["status"] < 500),
                "status_5xx_count": sum(1 for row in rows if row.get("status") and row["status"] >= 500),
                "average_response_time_ms": safe_mean(response_times),
                "p95_response_time_ms": percentile(response_times, 95),
                "top_failed_apis": [
                    {"endpoint": endpoint, "failures": count}
                    for endpoint, count in failed_api_counts.most_common(5)
                ],
            },
            "hourly_distribution": [
                {"hour": hour, "hits": hour_counts.get(hour, 0)}
                for hour in range(24)
            ],
        }
        self._log_summary = summary
        return summary

    def get_log_summary(self) -> Optional[Dict[str, Any]]:
        return self._log_summary

    def _extract_ticket_date(self, ticket: Dict[str, Any]) -> Optional[datetime]:
        comments = ticket.get("comments", [])
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            raw_date = comment.get("date")
            if isinstance(raw_date, datetime):
                return raw_date
            if isinstance(raw_date, str):
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                    try:
                        return datetime.strptime(raw_date, fmt)
                    except ValueError:
                        continue
        return None

    def _format_trend(self, trend: Dict[str, Counter]) -> List[Dict[str, Any]]:
        formatted = []
        for period in sorted(trend.keys()):
            categories = {category: trend[period].get(category, 0) for category in DEFAULT_CATEGORY_ORDER}
            formatted.append({
                "period": period,
                "total": sum(categories.values()),
                "categories": categories,
            })
        return formatted

    def _hour_rank(self, hour_counts: Counter, reverse: bool) -> List[Dict[str, Any]]:
        ranked = sorted(hour_counts.items(), key=lambda item: item[1], reverse=reverse)
        return [{"hour": hour, "hits": hits} for hour, hits in ranked[:3]]


analytics_service = AnalyticsService()
