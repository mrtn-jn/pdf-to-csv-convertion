"""
Logging configuration and utilities.
"""
import logging
import sys
from typing import Optional
from datetime import datetime
import os


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_colors: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        enable_colors: Whether to enable colored output for console

    Returns:
        Configured logger instance
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if enable_colors:
        colored_formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(colored_formatter)
    else:
        console_handler.setFormatter(simple_formatter)

    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        try:
            # Create log directory if it doesn't exist
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(file_handler)

        except Exception as e:
            root_logger.warning(f"Could not create file handler for {log_file}: {e}")

    # Create application logger
    app_logger = logging.getLogger("pdf_processor")
    app_logger.info(f"Logging initialized at level {level}")

    return app_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggingMixin:
    """Mixin class to add logging capabilities to any class"""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    def log_method_entry(self, method_name: str, **kwargs):
        """Log method entry with parameters"""
        params = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.debug(f"Entering {method_name}({params})")

    def log_method_exit(self, method_name: str, result=None):
        """Log method exit with result"""
        if result is not None:
            self.logger.debug(f"Exiting {method_name} with result: {type(result).__name__}")
        else:
            self.logger.debug(f"Exiting {method_name}")

    def log_error(self, error: Exception, context: str = None):
        """Log error with context"""
        context_str = f" in {context}" if context else ""
        self.logger.error(f"{type(error).__name__}{context_str}: {str(error)}")

    def log_warning(self, message: str, **kwargs):
        """Log warning with additional context"""
        if kwargs:
            context = ', '.join(f"{k}={v}" for k, v in kwargs.items())
            self.logger.warning(f"{message} ({context})")
        else:
            self.logger.warning(message)


def log_performance(func):
    """
    Decorator to log function performance metrics.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()

        try:
            logger.debug(f"Starting {func.__name__}")
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(f"{func.__name__} completed in {duration:.3f}s")
            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.error(f"{func.__name__} failed after {duration:.3f}s: {str(e)}")
            raise

    return wrapper


async def log_async_performance(func):
    """
    Async decorator to log function performance metrics.

    Args:
        func: Async function to decorate

    Returns:
        Decorated async function
    """
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()

        try:
            logger.debug(f"Starting {func.__name__}")
            result = await func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(f"{func.__name__} completed in {duration:.3f}s")
            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.error(f"{func.__name__} failed after {duration:.3f}s: {str(e)}")
            raise

    return wrapper