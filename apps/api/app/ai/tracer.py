import logging
import functools
import inspect
from typing import Callable

try:
    from langfuse import Langfuse
    from langfuse.decorators import observe
except ImportError:
    Langfuse = None
    observe = None

from app.core.config import settings

logger = logging.getLogger(__name__)

class NullTracer:
    """Fallback tracer when Langfuse is not configured or fails to initialize."""
    def observe(self, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def sync_wrapper(*args, **kwds):
                return func(*args, **kwds)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwds):
                return await func(*args, **kwds)

            if inspect.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator

class _TracerFactory:
    def __init__(self):
        self.langfuse = None
        self._initialized = False
        self._initialize()

    def _initialize(self):
        if self._initialized:
            return

        self._initialized = True

        if settings.langfuse_public_key and settings.langfuse_secret_key and settings.langfuse_host:
            try:
                # We simply instantiate to verify credentials are ok,
                # but the @observe decorator uses environment variables natively
                self.langfuse = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
                logger.info("Langfuse tracing initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                self.langfuse = None
        else:
            logger.info("Langfuse credentials not fully set. Using NullTracer.")

    @property
    def observe(self) -> Callable:
        if self.langfuse and observe:
            return observe
        return NullTracer().observe

tracer = _TracerFactory()
observe = tracer.observe
