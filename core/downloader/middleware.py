import time
import logging

logger = logging.getLogger("performance")


class PerformanceMonitoringMiddleware:
    """Track API response times"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        response["X-Response-Time"] = f"{duration:.3f}s"
        response["X-Response-Time-Ms"] = f"{int(duration * 1000)}ms"

        if duration > 0.5:
            logger.warning(
                f"SLOW: {request.method} {request.path} "
                f"took {duration * 1000:.0f}ms"
            )
        else:
            logger.info(
                f"FAST: {request.method} {request.path} "
                f"took {duration * 1000:.0f}ms"
            )

        return response