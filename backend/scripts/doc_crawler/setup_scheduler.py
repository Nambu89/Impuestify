"""
Setup Windows Task Scheduler for weekly document checks.

Run once to register the scheduled task:
    python -m backend.scripts.doc_crawler.setup_scheduler

To remove:
    python -m backend.scripts.doc_crawler.setup_scheduler --remove
"""
import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

TASK_NAME = "TaxIA-DocCrawler-Weekly"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BAT_FILE = Path(__file__).resolve().parent / "run_check.bat"

# Map day abbreviations to XML DaysOfWeek element names
DAY_MAP = {
    "MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday",
    "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday",
}


def _run_schtasks(cmd_str: str) -> tuple[int, str, str]:
    """Run schtasks command, return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd_str, capture_output=True, shell=True)
    stdout = result.stdout.decode("cp850", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("cp850", errors="replace") if result.stderr else ""
    return result.returncode, stdout, stderr


def _generate_task_xml(day: str, time: str, run_always: bool = False) -> str:
    """Generate XML task definition for Task Scheduler."""
    day_element = DAY_MAP.get(day.upper(), "Monday")

    # Calculate next occurrence for StartBoundary
    today = datetime.now()
    target_weekday = list(DAY_MAP.keys()).index(day.upper())
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_date = today + timedelta(days=days_ahead)
    start_boundary = f"{next_date.strftime('%Y-%m-%d')}T{time}:00"

    logon_type = "Password" if run_always else "InteractiveToken"

    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <DaysOfWeek>
          <{day_element} />
        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>{logon_type}</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{BAT_FILE}</Command>
      <WorkingDirectory>{PROJECT_ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""


def create_task(day: str = "MON", time: str = "09:00", run_always: bool = False) -> bool:
    """Register the weekly task in Windows Task Scheduler using XML import."""
    if not BAT_FILE.exists():
        print(f"Error: run_check.bat not found at {BAT_FILE}")
        return False

    mode = "Run whether user is logged on or not" if run_always else "Solo interactivo"
    print(f"Registrando tarea: {TASK_NAME}")
    print(f"  Dia: {day} a las {time}")
    print(f"  Modo: {mode}")
    print(f"  Script: {BAT_FILE}")
    print(f"  Working dir: {PROJECT_ROOT}")
    print()

    # Generate XML and write to temp file
    xml_content = _generate_task_xml(day, time, run_always=run_always)
    xml_path = BAT_FILE.parent / "_task.xml"
    xml_path.write_text(xml_content, encoding="utf-16")

    try:
        # When run_always=True, schtasks needs /RU to prompt for password
        cmd = f'schtasks /create /tn "{TASK_NAME}" /xml "{xml_path}" /f'
        if run_always:
            import getpass
            username = getpass.getuser()
            cmd += f' /RU "{username}"'
        rc, stdout, stderr = _run_schtasks(cmd)
        if rc == 0:
            print(f"Tarea '{TASK_NAME}' registrada correctamente.")
            print(f"Verificar: taskschd.msc o --check")
            if stdout.strip():
                print(stdout.strip())
            return True
        else:
            print(f"Error (code {rc}): {stderr.strip()}")
            return False
    finally:
        xml_path.unlink(missing_ok=True)


def remove_task() -> bool:
    """Remove the scheduled task."""
    rc, stdout, stderr = _run_schtasks(f'schtasks /delete /tn "{TASK_NAME}" /f')
    if rc == 0:
        print(f"Tarea '{TASK_NAME}' eliminada.")
        return True
    else:
        print(f"Error: {stderr.strip()}")
        return False


def check_task() -> bool:
    """Check if the task exists."""
    rc, stdout, stderr = _run_schtasks(f'schtasks /query /tn "{TASK_NAME}" /fo LIST')
    if rc == 0:
        print(f"Tarea '{TASK_NAME}' encontrada:")
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line and ":" in line:
                print(f"  {line}")
        return True
    else:
        print(f"Tarea '{TASK_NAME}' no encontrada.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Setup Windows Task Scheduler for TaxIA document crawler",
    )
    parser.add_argument("--remove", action="store_true", help="Remove the scheduled task")
    parser.add_argument("--check", action="store_true", help="Check if task exists")
    parser.add_argument("--day", default="MON", help="Day of week (MON-SUN, default: MON)")
    parser.add_argument("--time", default="09:00", help="Time (HH:MM, default: 09:00)")
    parser.add_argument("--run-always", action="store_true",
                        help="Run whether user is logged on or not (prompts for password)")

    args = parser.parse_args()

    if args.remove:
        remove_task()
    elif args.check:
        check_task()
    else:
        create_task(day=args.day, time=args.time, run_always=args.run_always)


if __name__ == "__main__":
    main()
