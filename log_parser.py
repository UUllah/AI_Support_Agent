import math
import re
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional


APACHE_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<endpoint>[^\s"]+)(?:\s+[^"]+)?"\s+(?P<status>\d{3})(?:\s+\S+)?(?:\s+.*?(?P<response_time>[\d.]+(?:ms|s|us)?))?$',
    re.IGNORECASE,
)
ISO_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\s+(?P<ip>\S+)\s+(?P<method>[A-Z]+)\s+(?P<endpoint>/\S+)\s+(?P<status>\d{3})(?:\s+(?P<response_time>[\d.]+(?:ms|s|us)?))?',
    re.IGNORECASE,
)


class LogParser:
    def parse_upload(self, filename: str, content: bytes) -> Dict[str, Any]:
        text = content.decode("utf-8", errors="ignore")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sample = lines[:100]

        parsed_rows = [row for row in (self.parse_line(line) for line in lines) if row]
        detected_pattern = self.detect_pattern(sample)

        return {
            "filename": filename,
            "detected_pattern": detected_pattern,
            "raw_preview": sample,
            "parsed_preview": parsed_rows[:10],
            "field_inference": self.infer_fields(parsed_rows[:25]),
            "parsed_rows": parsed_rows,
        }

    def detect_pattern(self, sample_lines: List[str]) -> str:
        apache_hits = sum(1 for line in sample_lines if APACHE_PATTERN.match(line))
        iso_hits = sum(1 for line in sample_lines if ISO_PATTERN.match(line))
        if apache_hits >= iso_hits and apache_hits > 0:
            return "apache_common_or_combined"
        if iso_hits > 0:
            return "iso_structured"
        return "generic_access_log"

    def infer_fields(self, rows: List[Dict[str, Any]]) -> Dict[str, bool]:
        fields = ["timestamp", "endpoint", "response_time", "status", "ip", "method"]
        return {field: any(row.get(field) is not None for row in rows) for field in fields}

    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        for parser in (self._parse_apache, self._parse_iso, self._parse_generic):
            parsed = parser(line)
            if parsed:
                return parsed
        return None

    def _parse_apache(self, line: str) -> Optional[Dict[str, Any]]:
        match = APACHE_PATTERN.match(line)
        if not match:
            return None
        groups = match.groupdict()
        return self._finalize(groups)

    def _parse_iso(self, line: str) -> Optional[Dict[str, Any]]:
        match = ISO_PATTERN.match(line)
        if not match:
            return None
        groups = match.groupdict()
        return self._finalize(groups)

    def _parse_generic(self, line: str) -> Optional[Dict[str, Any]]:
        method_match = re.search(r'\b(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\b', line)
        endpoint_match = re.search(r'(/[^\s"?]+(?:\?[^\s"]+)?)', line)
        status_match = re.search(r'\b([45]?\d{2}|200|201|202|204|301|302|304)\b', line)
        ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', line)
        time_match = re.search(r'(?P<response_time>[\d.]+(?:ms|s|us))', line, re.IGNORECASE)
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)', line)

        if not method_match or not endpoint_match or not status_match:
            return None

        return self._finalize(
            {
                "timestamp": timestamp_match.group(1) if timestamp_match else None,
                "method": method_match.group(1),
                "endpoint": endpoint_match.group(1),
                "status": status_match.group(1),
                "ip": ip_match.group(0) if ip_match else None,
                "response_time": time_match.group("response_time") if time_match else None,
            }
        )

    def _finalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = self._parse_timestamp(raw.get("timestamp"))
        response_time = self._parse_response_time(raw.get("response_time"))
        status = int(raw["status"]) if raw.get("status") else None
        return {
            "timestamp": timestamp.isoformat() if timestamp else None,
            "hour": timestamp.hour if timestamp else None,
            "minute": timestamp.strftime("%Y-%m-%d %H:%M") if timestamp else None,
            "endpoint": raw.get("endpoint"),
            "response_time": response_time,
            "status": status,
            "ip": raw.get("ip"),
            "method": raw.get("method"),
        }

    def _parse_timestamp(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None

        cleaned = value.strip()
        for fmt in (
            "%d/%b/%Y:%H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        return None

    def _parse_response_time(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None

        cleaned = str(value).strip().lower()
        if cleaned.endswith("ms"):
            return float(cleaned[:-2])
        if cleaned.endswith("us"):
            return float(cleaned[:-2]) / 1000.0
        if cleaned.endswith("s"):
            return float(cleaned[:-1]) * 1000.0
        try:
            numeric = float(cleaned)
            return numeric * 1000.0 if numeric < 20 else numeric
        except ValueError:
            return None


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil((pct / 100) * len(ordered)) - 1))
    return round(ordered[index], 2)


def safe_mean(values: List[float]) -> float:
    return round(mean(values), 2) if values else 0.0
