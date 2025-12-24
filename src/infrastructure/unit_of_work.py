from contextlib import AbstractContextManager


class UnitOfWork(AbstractContextManager):
   def __init__(self, connection):
      self.connection = connection
      self._cursor = None

   def __enter__(self):
      self._cursor = self.connection.cursor()
      return self

   @property
   def cursor(self):
      return self._cursor

   def commit(self):
      self.connection.commit()

   def rollback(self):
      self.connection.rollback()

   def __exit__(self, exc_type, exc, tb):
      try:
         if exc:
            self.rollback()
         else:
            self.commit()
      finally:
         if self._cursor:
            self._cursor.close()
