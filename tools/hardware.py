import shutil
import os
from strands import tool
import platform

def _gb(n_bytes: int) -> float:
    return round(n_bytes / 1e9, 1)

@tool(
    name="hardware_information",
    description=(
        "Use quando o usuário perguntar sobre o computador: sistema operacional, "
        "memória RAM ou espaço em disco. Retorna um dicionário com os valores em GB."
    ),
)
def get_hardware_information():
  total, used, _ = shutil.disk_usage('/')
  ram = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')

  return {
    "system_name": f"{platform.freedesktop_os_release()["PRETTY_NAME"]} - {platform.system()}",
    "ram_total_gb": _gb(ram),
    "disco_total_gb": _gb(total),
    "disco_em_uso_gb": _gb(used),
  }
