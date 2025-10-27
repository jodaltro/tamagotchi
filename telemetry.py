"""
Telemetry and metrics tracking for the virtual pet system.

This module tracks and exposes key metrics as specified:
- Latency (p50/p95) for Ollama calls
- Token counts (input/output)
- Self-Consistency Rate
- Commitment Resolution Rate
- Tokens per turn

Metrics are collected during runtime and can be queried for monitoring.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)


@dataclass
class TurnMetrics:
    """Metrics for a single conversation turn."""
    timestamp: datetime
    latency_ms: float
    tokens_in: int
    tokens_out: int
    consistency_passed: bool
    consistency_issues: int
    model: str = "unknown"
    
    def __repr__(self) -> str:
        return f"TurnMetrics(latency={self.latency_ms:.0f}ms, tokens={self.tokens_in}→{self.tokens_out}, consistent={self.consistency_passed})"


@dataclass
class CommitmentMetrics:
    """Metrics for commitment tracking."""
    timestamp: datetime
    commitments_created: int = 0
    commitments_fulfilled: int = 0
    commitments_active: int = 0
    
    def get_resolution_rate(self) -> float:
        """Calculate commitment resolution rate."""
        total = self.commitments_created + self.commitments_fulfilled
        if total == 0:
            return 0.0
        return self.commitments_fulfilled / total


class TelemetryCollector:
    """
    Collects and aggregates metrics for the virtual pet system.
    """
    
    def __init__(self):
        """Initialize telemetry collector."""
        self.turn_metrics: List[TurnMetrics] = []
        self.commitment_metrics: List[CommitmentMetrics] = []
        
        logger.info("📊 TelemetryCollector initialized")
    
    def record_turn(
        self,
        latency_ms: float,
        tokens_in: int,
        tokens_out: int,
        consistency_passed: bool,
        consistency_issues: int = 0,
        model: str = "unknown"
    ) -> None:
        """
        Record metrics for a conversation turn.
        
        Args:
            latency_ms: Response generation latency in milliseconds
            tokens_in: Number of input tokens
            tokens_out: Number of output tokens
            consistency_passed: Whether SCG check passed
            consistency_issues: Number of consistency issues detected
            model: Model used for generation
        """
        turn = TurnMetrics(
            timestamp=datetime.utcnow(),
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            consistency_passed=consistency_passed,
            consistency_issues=consistency_issues,
            model=model
        )
        
        self.turn_metrics.append(turn)
        
        logger.debug(f"📝 Recorded turn metrics: {turn}")
    
    def record_commitments(
        self,
        created: int = 0,
        fulfilled: int = 0,
        active: int = 0
    ) -> None:
        """
        Record commitment metrics.
        
        Args:
            created: Number of new commitments created
            fulfilled: Number of commitments fulfilled
            active: Number of currently active commitments
        """
        metrics = CommitmentMetrics(
            timestamp=datetime.utcnow(),
            commitments_created=created,
            commitments_fulfilled=fulfilled,
            commitments_active=active
        )
        
        self.commitment_metrics.append(metrics)
        
        logger.debug(f"📝 Recorded commitment metrics: resolution_rate={metrics.get_resolution_rate():.2%}")
    
    def get_latency_percentiles(self, percentiles: List[int] = [50, 95]) -> Dict[int, float]:
        """
        Calculate latency percentiles.
        
        Args:
            percentiles: List of percentile values to calculate (e.g., [50, 95])
        
        Returns:
            Dictionary mapping percentile to latency in ms
        """
        if not self.turn_metrics:
            return {p: 0.0 for p in percentiles}
        
        latencies = [t.latency_ms for t in self.turn_metrics]
        
        result = {}
        for p in percentiles:
            if len(latencies) == 1:
                result[p] = latencies[0]
            else:
                result[p] = statistics.quantiles(latencies, n=100)[p - 1] if p <= 100 else latencies[-1]
        
        return result
    
    def get_consistency_rate(self) -> float:
        """
        Calculate the self-consistency rate.
        
        Returns:
            Percentage of turns that passed consistency check
        """
        if not self.turn_metrics:
            return 0.0
        
        passed = sum(1 for t in self.turn_metrics if t.consistency_passed)
        return (passed / len(self.turn_metrics)) * 100
    
    def get_commitment_resolution_rate(self) -> float:
        """
        Calculate the commitment resolution rate.
        
        Returns:
            Percentage of commitments fulfilled
        """
        if not self.commitment_metrics:
            return 0.0
        
        total_created = sum(m.commitments_created for m in self.commitment_metrics)
        total_fulfilled = sum(m.commitments_fulfilled for m in self.commitment_metrics)
        
        if total_created == 0:
            return 0.0
        
        return (total_fulfilled / total_created) * 100
    
    def get_avg_tokens_per_turn(self) -> Dict[str, float]:
        """
        Calculate average tokens per turn.
        
        Returns:
            Dictionary with avg_in, avg_out, avg_total
        """
        if not self.turn_metrics:
            return {"avg_in": 0.0, "avg_out": 0.0, "avg_total": 0.0}
        
        avg_in = statistics.mean(t.tokens_in for t in self.turn_metrics)
        avg_out = statistics.mean(t.tokens_out for t in self.turn_metrics)
        
        return {
            "avg_in": avg_in,
            "avg_out": avg_out,
            "avg_total": avg_in + avg_out
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of all metrics.
        
        Returns:
            Dictionary with all key metrics
        """
        latency_p = self.get_latency_percentiles([50, 95])
        tokens = self.get_avg_tokens_per_turn()
        
        return {
            "total_turns": len(self.turn_metrics),
            "latency_p50_ms": latency_p.get(50, 0.0),
            "latency_p95_ms": latency_p.get(95, 0.0),
            "avg_tokens_in": tokens["avg_in"],
            "avg_tokens_out": tokens["avg_out"],
            "avg_tokens_total": tokens["avg_total"],
            "consistency_rate_pct": self.get_consistency_rate(),
            "commitment_resolution_rate_pct": self.get_commitment_resolution_rate(),
            "total_consistency_issues": sum(t.consistency_issues for t in self.turn_metrics),
            "models_used": list(set(t.model for t in self.turn_metrics))
        }
    
    def get_detailed_report(self, recent_n: Optional[int] = None) -> str:
        """
        Generate a detailed text report of metrics.
        
        Args:
            recent_n: If provided, only report on the N most recent turns
        
        Returns:
            Formatted report string
        """
        metrics_to_analyze = self.turn_metrics
        if recent_n and len(metrics_to_analyze) > recent_n:
            metrics_to_analyze = metrics_to_analyze[-recent_n:]
        
        # Calculate stats on the selected metrics
        if not metrics_to_analyze:
            return "No metrics recorded yet."
        
        latencies = [t.latency_ms for t in metrics_to_analyze]
        tokens_in = [t.tokens_in for t in metrics_to_analyze]
        tokens_out = [t.tokens_out for t in metrics_to_analyze]
        consistent = [t.consistency_passed for t in metrics_to_analyze]
        
        report_parts = []
        report_parts.append("=" * 60)
        report_parts.append("TELEMETRY REPORT")
        report_parts.append("=" * 60)
        
        if recent_n:
            report_parts.append(f"Analyzing last {len(metrics_to_analyze)} turns (of {len(self.turn_metrics)} total)")
        else:
            report_parts.append(f"Total turns: {len(metrics_to_analyze)}")
        
        report_parts.append("")
        report_parts.append("LATENCY METRICS:")
        report_parts.append(f"  p50: {statistics.median(latencies):.0f} ms")
        if len(latencies) > 1:
            p95 = statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 100 else max(latencies)
            report_parts.append(f"  p95: {p95:.0f} ms")
        report_parts.append(f"  min: {min(latencies):.0f} ms")
        report_parts.append(f"  max: {max(latencies):.0f} ms")
        report_parts.append(f"  avg: {statistics.mean(latencies):.0f} ms")
        
        report_parts.append("")
        report_parts.append("TOKEN METRICS:")
        report_parts.append(f"  Input tokens (avg):  {statistics.mean(tokens_in):.1f}")
        report_parts.append(f"  Output tokens (avg): {statistics.mean(tokens_out):.1f}")
        report_parts.append(f"  Total tokens (avg):  {statistics.mean(tokens_in) + statistics.mean(tokens_out):.1f}")
        
        report_parts.append("")
        report_parts.append("CONSISTENCY METRICS:")
        consistency_rate = (sum(consistent) / len(consistent)) * 100
        report_parts.append(f"  Consistency rate: {consistency_rate:.1f}%")
        report_parts.append(f"  Passed: {sum(consistent)}")
        report_parts.append(f"  Failed: {len(consistent) - sum(consistent)}")
        
        if self.commitment_metrics:
            report_parts.append("")
            report_parts.append("COMMITMENT METRICS:")
            total_created = sum(m.commitments_created for m in self.commitment_metrics)
            total_fulfilled = sum(m.commitments_fulfilled for m in self.commitment_metrics)
            resolution_rate = (total_fulfilled / max(1, total_created)) * 100
            report_parts.append(f"  Created: {total_created}")
            report_parts.append(f"  Fulfilled: {total_fulfilled}")
            report_parts.append(f"  Resolution rate: {resolution_rate:.1f}%")
        
        report_parts.append("")
        report_parts.append("=" * 60)
        
        return "\n".join(report_parts)
    
    def reset(self) -> None:
        """Reset all collected metrics."""
        self.turn_metrics.clear()
        self.commitment_metrics.clear()
        logger.info("🔄 Telemetry metrics reset")
    
    def __repr__(self) -> str:
        return f"TelemetryCollector(turns={len(self.turn_metrics)}, consistency={self.get_consistency_rate():.1f}%)"


# Global telemetry instance
_telemetry: Optional[TelemetryCollector] = None


def get_telemetry() -> TelemetryCollector:
    """Get or create the global telemetry collector."""
    global _telemetry
    
    if _telemetry is None:
        _telemetry = TelemetryCollector()
    
    return _telemetry
