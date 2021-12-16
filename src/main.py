import frontend.server as s
import logging
from rich.logging import RichHandler


log_level = "INFO"
logging.basicConfig(
    level=log_level,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("rich")

if __name__ == "__main__":
    s.app.run()
