"""vibe/core/plugins/resilience.py

────────────────────────────────────────────────────────────────────────────
Plugin resilience — circuit breaker for plugin operations.

Provides circuit breaker protection for plugin lifecycle and tool hook
operations. Prevents a misbehaving plugin from blocking or
crashing the entire plugin system.
"""

from __future__ import annotations

import asyncio
import logging

import pybreaker
import structlog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibe.core.config import VibeConfig

logger = structlog.get_logger(__name__)


class PluginCircuitListener:
    """Circuit breaker listener that logs state changes."""

    def __init__(self, name: str, plugin_name: str | None = None, file_path: str | None = None, line_number: int | None = None) -> None:
        self._name = name
        self._plugin_name = plugin_name
        self._file_path = file_path
        self._line_number = line_number

    def __call__(self, cb: pybreaker.CircuitBreaker, ex: BaseException | None) -> None:
        """Called on state changes and failures."""
        state = cb.current_state
        context = {
            "circuit_name": self._name,
            "plugin_name": self._plugin_name,
            "file_path": self._file_path,
            "line_number": self._line_number
        }
        
        if ex is not None:
            logger.error(
                "Circuit breaker failure recorded",
                circuit_name=self._name,
                state=state,
                error_type=type(ex).__name__,
                error_message=str(ex),
                extra={"context": context},
                exc_info=True
            )
        elif state == pybreaker.STATE_OPEN:
            logger.warning(
                "Circuit breaker state change",
                circuit_name=self._name,
                old_state="closed_or_half_open",
                new_state="open",
                extra={"context": context}
            )
        elif state == pybreaker.STATE_CLOSED:
            logger.info(
                "Circuit breaker state change",
                circuit_name=self._name,
                old_state="open_or_half_open",
                new_state="closed",
                extra={"context": context}
            )
        elif state == pybreaker.STATE_HALF_OPEN:
            logger.warning(
                "Circuit breaker state change",
                circuit_name=self._name,
                old_state="open",
                new_state="half_open",
                extra={"context": context}
            )


def _get_circuit_breaker(config: VibeConfig) -> pybreaker.CircuitBreaker:
    """Create a circuit breaker instance configured from VibeConfig."""
    threshold = getattr(
        config,
        "plugin_circuit_breaker_failure_threshold",
        3,
    )
    timeout = getattr(
        config,
        "plugin_circuit_breaker_recovery_timeout_sec",
        30.0,
    )

    breaker = pybreaker.CircuitBreaker(
        fail_max=threshold,
        reset_timeout=timeout,
        exclude=[KeyboardInterrupt, asyncio.CancelledError],
    )
    listener = PluginCircuitListener("plugin_ops", plugin_name=None, file_path=None, line_number=None)
    breaker.add_listener(listener)  # type: ignore[arg-type]
    return breaker


PLUGIN_CIRCUIT_BREAKER: pybreaker.CircuitBreaker | None = None


def init_plugin_circuit_breaker(config: VibeConfig) -> pybreaker.CircuitBreaker:
    """Initialize and return the global plugin circuit breaker."""
    global PLUGIN_CIRCUIT_BREAKER  # noqa: PLW0603
    PLUGIN_CIRCUIT_BREAKER = _get_circuit_breaker(config)
    return PLUGIN_CIRCUIT_BREAKER


def get_plugin_circuit_breaker() -> pybreaker.CircuitBreaker:
    """Get the initialized plugin circuit breaker."""
    if PLUGIN_CIRCUIT_BREAKER is None:
        raise RuntimeError("Plugin circuit breaker not initialized")
    return PLUGIN_CIRCUIT_BREAKER