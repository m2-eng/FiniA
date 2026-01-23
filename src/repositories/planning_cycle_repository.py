from repositories.base import BaseRepository


class PlanningCycleRepository(BaseRepository):
   def upsert(self, cycle_id: int, cycle_name: str, period_value: float, period_unit: str) -> None:
      sql = (
         "INSERT INTO tbl_planningCycle (id, cycle, periodValue, periodUnit, dateImport) "
         "VALUES (%s, %s, %s, %s, NOW()) "
         "ON DUPLICATE KEY UPDATE cycle = VALUES(cycle), "
         "periodValue = VALUES(periodValue), periodUnit = VALUES(periodUnit)"
      )
      self.cursor.execute(sql, (cycle_id, cycle_name, period_value, period_unit))
