class BaseRepository:
   def __init__(self, uow_or_cursor):
      """Initialize repository with either UnitOfWork or raw DB cursor.

      Args:
         uow_or_cursor: UnitOfWork instance (with .cursor attribute) or a raw DB cursor
      """
      if hasattr(uow_or_cursor, "cursor"):
         # UnitOfWork or connection wrapper
         self.uow = uow_or_cursor
         self.cursor = uow_or_cursor.cursor
      else:
         # Raw cursor passed directly
         self.uow = None
         self.cursor = uow_or_cursor
