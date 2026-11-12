from datetime import datetime
from strands import tool

@tool
def currentDateAndTime() -> str:
  return datetime.now().strftime("%d/%m/%Y %H:%M")