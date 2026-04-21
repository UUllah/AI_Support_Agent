import html
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Login Issues": [
        "login", "log in", "sign in", "signin", "password", "credentials", "unable to login",
        "authentication", "reset password", "otp", "prelogin",
    ],
    "Transaction Failures": [
        "transaction failed", "transaction fail", "reversal", "reversed", "declined", "transfer failed",
        "payment failed", "debit", "credit not posted", "posting issue", "fund transfer",
    ],
    "ATM / Cash Out Issues": [
        "atm", "cash out", "cashout", "withdrawal", "dispense", "card retained", "cash withdrawal",
        "atm switch", "cash not received",
    ],
    "Mobile Banking Issues": [
        "mobile banking", "mobile app", "app issue", "android", "ios", "device", "biometric",
        "app crash", "app login", "4g", "local internet",
    ],
    "UAT Setup Requests": [
        "uat", "test environment", "testing", "uat setup", "uat release", "uat server", "user creation",
        "whitelist", "uat access", "test user",
    ],
    "DR / Failover Setup": [
        "dr", "disaster recovery", "failover", "drill", "site switch", "replication", "switchover",
        "dr setup", "fail over",
    ],
    "API Integration Issues": [
        "api", "integration", "endpoint", "webhook", "host to host", "service call", "payload",
        "request timeout", "response mapping", "soap", "rest api",
    ],
    "Performance / Slow Response": [
        "slow", "slowness", "latency", "timeout", "performance", "slow response", "takes time",
        "hang", "delayed", "response time",
    ],
    "Configuration / Deployment Issues": [
        "deployment", "deploy", "release", "configuration", "config", "production rollout", "cab",
        "db script", "installation", "patch", "server config", "compile release",
    ],
}

NOISE_PATTERNS = [
    r"\bdear\s+(team|all|sir|madam|support|sharif|yaseen|muhammad|hello team)\b[:,]?",
    r"\bhello\s+(team|all|sir|madam|support|yaseen|muhammad)\b[:,]?",
    r"\bhi\s+(team|all|support|tropical bank team)\b[:,]?",
    r"\bbest\s+regards\b[:]?(?:\s+[a-z .]+)?",
    r"\bregards\b[:]?(?:\s+[a-z .]+)?",
    r"\bkindly\b",
    r"\bplease\s+connect\b",
    r"\bpfa\b",
]


class TicketClassifier:
    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        cleaned = html.unescape(str(text))
        cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<.*?>", " ", cleaned)
        cleaned = cleaned.replace("\r", "\n")
        for pattern in NOISE_PATTERNS:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def build_ticket_text(self, ticket: Dict[str, Any]) -> str:
        parts: List[str] = []
        for field in ("subject", "summary"):
            value = ticket.get(field)
            if value:
                parts.append(self.clean_text(value))

        comments = ticket.get("comments", [])
        for comment in comments[:5]:
            if isinstance(comment, dict):
                value = comment.get("text", "")
            else:
                value = str(comment)
            if value:
                parts.append(self.clean_text(value))

        if not parts and ticket.get("text"):
            parts.append(self.clean_text(ticket["text"]))

        return " ".join(part for part in parts if part).strip()

    def _rule_scores(self, ticket_text: str) -> Dict[str, int]:
        normalized = ticket_text.lower()
        scores: Dict[str, int] = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                score += normalized.count(keyword.lower())
            scores[category] = score
        return scores

    def summarize_insight(self, ticket: Dict[str, Any]) -> str:
        subject = self.clean_text(ticket.get("subject", ""))
        summary = self.clean_text(ticket.get("summary", ""))
        insight_parts = [part for part in [subject, summary] if part]

        comments = ticket.get("comments", [])
        for comment in comments[:3]:
            text = comment.get("text", "") if isinstance(comment, dict) else str(comment)
            text = self.clean_text(text)
            if text:
                insight_parts.append(text)
            if len(". ".join(insight_parts)) > 240:
                break

        insight = ". ".join(insight_parts)
        if len(insight) > 240:
            insight = insight[:237] + "..."
        return insight or "No additional insight available."

    def classify_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        ticket_text = self.build_ticket_text(ticket)
        scores = self._rule_scores(ticket_text)
        category, score = max(scores.items(), key=lambda item: item[1]) if scores else ("Other", 0)
        if score <= 0:
            category = "Other"

        return {
            "ticket_id": ticket.get("ticket_id"),
            "category": category,
            "score": score,
            "subject": ticket.get("subject", ""),
            "summary": self.clean_text(ticket.get("summary", "")),
            "insight": self.summarize_insight(ticket),
        }
