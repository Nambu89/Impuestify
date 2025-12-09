"""
Deadline Calculator for AEAT notifications.

Calculates exact dates from relative expressions like "10 días hábiles".
Considers national and regional holidays.
"""
from datetime import datetime, timedelta
from typing import List, Optional
import re


class DeadlineCalculator:
    """Calculate exact deadlines from relative dates in AEAT notifications."""
    
    # Festivos nacionales 2024-2025
    NATIONAL_HOLIDAYS_2024 = [
        "2024-01-01",  # Año Nuevo
        "2024-01-06",  # Reyes
        "2024-03-29",  # Viernes Santo
        "2024-05-01",  # Día del Trabajo
        "2024-08-15",  # Asunción
        "2024-10-12",  # Fiesta Nacional
        "2024-11-01",  # Todos los Santos
        "2024-12-06",  # Constitución
        "2024-12-25",  # Navidad
    ]
    
    NATIONAL_HOLIDAYS_2025 = [
        "2025-01-01",  # Año Nuevo
        "2025-01-06",  # Reyes
        "2025-04-18",  # Viernes Santo
        "2025-05-01",  # Día del Trabajo
        "2025-08-15",  # Asunción
        "2025-10-12",  # Fiesta Nacional
        "2025-11-01",  # Todos los Santos
        "2025-12-06",  # Constitución
        "2025-12-08",  # Inmaculada
        "2025-12-25",  # Navidad
    ]
    
    # Festivos autonómicos (sample, debería ampliarse)
    REGIONAL_HOLIDAYS = {
        "madrid": {
            "2024": ["2024-05-02", "2024-05-15"],  # Comunidad, San Isidro
            "2025": ["2025-05-02", "2025-05-15"]
        },
        "cataluña": {
            "2024": ["2024-06-24", "2024-09-11", "2024-12-26"],  # Sant Joan, Diada, Sant Esteve
            "2025": ["2025-06-24", "2025-09-11", "2025-12-26"]
        },
        "país vasco": {
            "2024": ["2024-03-28", "2024-07-25", "2024-10-25"],
            "2025": ["2025-03-28", "2025-07-25", "2025-10-25"]
        },
        "aragón": {
            "2024": ["2024-04-23", "2024-10-12"],
            "2025": ["2025-04-23", "2025-10-12"]
        },
        # Añadir más CCAA según necesidad
    }
    
    def __init__(self):
        self.all_holidays = (
            self.NATIONAL_HOLIDAYS_2024 + 
            self.NATIONAL_HOLIDAYS_2025
        )
    
    def calculate_business_days(
        self,
        start_date: str,
        num_days: int,
        region: Optional[str] = None
    ) -> str:
        """
        Calculate exact date after N business days.
        
        Args:
            start_date: ISO date string (YYYY-MM-DD)
            num_days: Number of business days to add
            region: Autonomous community (lowercase), optional
        
        Returns:
            ISO date string of the deadline
        
        Example:
            >>> calc = DeadlineCalculator()
            >>> calc.calculate_business_days("2024-12-10", 10, "madrid")
            "2024-12-26"  # Skips weekends and Christmas
        """
        current = datetime.fromisoformat(start_date)
        year = str(current.year)
        
        # Get regional holidays for this year
        regional = []
        if region:
            region_key = region.lower().strip()
            if region_key in self.REGIONAL_HOLIDAYS:
                regional = self.REGIONAL_HOLIDAYS[region_key].get(year, [])
        
        days_counted = 0
        
        while days_counted < num_days:
            current += timedelta(days=1)
            
            # Skip weekends (Saturday=5, Sunday=6)
            if current.weekday() >= 5:
                continue
            
            # Skip holidays
            date_str = current.strftime("%Y-%m-%d")
            if date_str in self.all_holidays or date_str in regional:
                continue
            
            days_counted += 1
        
        return current.strftime("%Y-%m-%d")
    
    def calculate_calendar_days(
        self,
        start_date: str,
        num_days: int
    ) -> str:
        """
        Calculate exact date after N calendar days (not business days).
        
        Args:
            start_date: ISO date string
            num_days: Number of calendar days
        
        Returns:
            ISO date string
        """
        current = datetime.fromisoformat(start_date)
        target = current + timedelta(days=num_days)
        return target.strftime("%Y-%m-%d")
    
    def calculate_months(
        self,
        start_date: str,
        num_months: int
    ) -> str:
        """
        Calculate date after N months.
        
        Args:
            start_date: ISO date string
            num_months: Number of months
        
        Returns:
            ISO date string
        """
        from dateutil.relativedelta import relativedelta
        
        current = datetime.fromisoformat(start_date)
        target = current + relativedelta(months=num_months)
        return target.strftime("%Y-%m-%d")
    
    def extract_deadlines_from_text(
        self,
        text: str,
        notification_date: str
    ) -> List[dict]:
        """
        Extract deadline expressions from notification text.
        
        Args:
            text: Notification text content
            notification_date: Date the notification was received
        
        Returns:
            List of deadline dicts with calculated dates
        
        Patterns detected:
        - "10 días hábiles"
        - "plazo de un mes" / "plazo de 1 mes"
        - "30 días naturales"
        - "antes del 31 de diciembre de 2024"
        """
        deadlines = []
        
        # Start date is "día siguiente" to notification
        start = datetime.fromisoformat(notification_date) + timedelta(days=1)
        start_str = start.strftime("%Y-%m-%d")
        
        # Pattern 1: X días hábiles
        pattern1 = r'(\d+)\s+días?\s+hábiles?'
        for match in re.finditer(pattern1, text, re.IGNORECASE):
            num_days = int(match.group(1))
            deadline_date = self.calculate_business_days(start_str, num_days)
            
            deadlines.append({
                'type': 'business_days',
                'value': num_days,
                'text': match.group(0),
                'date': deadline_date,
                'description': f'{num_days} días hábiles'
            })
        
        # Pattern 2: X días naturales / X días (sin "hábiles")
        pattern2 = r'(\d+)\s+días?\s+(?:naturales?|(?!hábiles))'
        for match in re.finditer(pattern2, text, re.IGNORECASE):
            num_days = int(match.group(1))
            deadline_date = self.calculate_calendar_days(start_str, num_days)
            
            deadlines.append({
                'type': 'calendar_days',
                'value': num_days,
                'text': match.group(0),
                'date': deadline_date,
                'description': f'{num_days} días naturales'
            })
        
        # Pattern 3: Plazo de X mes/meses
        pattern3 = r'plazo\s+de\s+(?:un|1|(\d+))\s+mes(?:es)?'
        for match in re.finditer(pattern3, text, re.IGNORECASE):
            num_months = int(match.group(1)) if match.group(1) else 1
            deadline_date = self.calculate_months(start_str, num_months)
            
            deadlines.append({
                'type': 'months',
                'value': num_months,
                'text': match.group(0),
                'date': deadline_date,
                'description': f'{num_months} mes{"es" if num_months > 1 else ""}'
            })
        
        # Pattern 4: Absolute dates "antes del DD de MONTH de YYYY"
        months_es = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        pattern4 = r'antes\s+del?\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
        for match in re.finditer(pattern4, text, re.IGNORECASE):
            day = int(match.group(1))
            month_name = match.group(2).lower()
            year = int(match.group(3))
            
            if month_name in months_es:
                month = months_es[month_name]
                deadline_date = f"{year:04d}-{month:02d}-{day:02d}"
                
                deadlines.append({
                    'type': 'absolute',
                    'text': match.group(0),
                    'date': deadline_date,
                    'description': f'{day} de {month_name} de {year}'
                })
        
        return deadlines
    
    def days_remaining(self, deadline_date: str) -> int:
        """
        Calculate days remaining until deadline.
        
        Args:
            deadline_date: ISO date string
        
        Returns:
            Number of days (negative if overdue)
        """
        today = datetime.now().date()
        deadline = datetime.fromisoformat(deadline_date).date()
        delta = (deadline - today).days
        return delta
    
    def is_urgent(self, deadline_date: str, threshold_days: int = 5) -> bool:
        """
        Check if deadline is urgent.
        
        Args:
            deadline_date: ISO date string
            threshold_days: Days threshold for urgency
        
        Returns:
            True if deadline is within threshold
        """
        remaining = self.days_remaining(deadline_date)
        return 0 <= remaining <= threshold_days
