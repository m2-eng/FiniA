from repositories.base import BaseRepository


class PlanningCycleRepository(BaseRepository):
   def insert_ignore(self, cycle_id: int, cycle_name: str) -> None:
      sql = "INSERT IGNORE INTO tbl_planningCycle (id, cycle, dateImport) VALUES (%s, %s, NOW())"
      self.cursor.execute(sql, (cycle_id, cycle_name))
