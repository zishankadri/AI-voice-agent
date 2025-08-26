import threading
import logging

logger = logging.getLogger(__name__)

def run_after_delay(delay_seconds, func, *args, **kwargs):
    """
    Runs a function after a specified delay (in seconds).
    :param delay_seconds: Time in seconds to delay
    :param func: Function to call
    :param args: Positional arguments for func
    :param kwargs: Keyword arguments for func
    """
    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in delayed task: {e}", exc_info=True)

    timer = threading.Timer(delay_seconds, wrapper)
    timer.daemon = True  # Doesn't block process exit
    timer.start()
    return timer  # Return if you want to cancel later
