import sys
from loguru import logger


logger.remove()
#logger.add("output.log")
logger.add(sink=sys.stdout, format="<white>NotPixel</white>"
                                   " | <white>{time:YYYY-MM-DD HH:mm:ss}</white>"
                                   " | <level>{level: <8}</level>"
                                   " - <white><b>{message}</b></white>")
logger = logger.opt(colors=True)
