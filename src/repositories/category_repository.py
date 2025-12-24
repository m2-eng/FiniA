from repositories.base import BaseRepository


class CategoryRepository(BaseRepository):
   def insert_ignore(self, category_id: int, category_name: str, parent_category_id: int = None) -> None:
      """
      Insert a category into tbl_category.
      
      Args:
         category_id: Unique ID for the category
         category_name: Name of the category
         parent_category_id: ID of the parent category (for subcategories), None for top-level
      """
      sql = "INSERT IGNORE INTO tbl_category (id, name, category, dateImport) VALUES (%s, %s, %s, NOW())"
      self.cursor.execute(sql, (category_id, category_name, parent_category_id))

   def get_category_by_name(self, name: str) -> int:
      """
      Get category ID by name.
      
      Args:
         name: Category name
         
      Returns:
         Category ID if found, None otherwise
      """
      sql = "SELECT id FROM tbl_category WHERE name = %s"
      self.cursor.execute(sql, (name,))
      result = self.cursor.fetchone()
      return result[0] if result else None

   def get_category_id_by_name_and_parent(self, name: str, parent_id: int = None) -> int:
      """
      Get category ID by name and parent category ID.
      
      Args:
         name: Category name
         parent_id: Parent category ID (None for root categories)
         
      Returns:
         Category ID if found, None otherwise
      """
      sql = "SELECT id FROM tbl_category WHERE name = %s AND category <=> %s"
      self.cursor.execute(sql, (name, parent_id))
      result = self.cursor.fetchone()
      return result[0] if result else None

   def get_max_category_id(self) -> int:
      """
      Get the maximum category ID in the database.
      
      Returns:
         Maximum ID, or 0 if no categories exist
      """
      sql = "SELECT COALESCE(MAX(id), 0) FROM tbl_category"
      self.cursor.execute(sql)
      result = self.cursor.fetchone()
      return result[0] if result else 0

   def insert_category(self, category_id: int, category_name: str, parent_category_id: int = None) -> None:
      """
      Insert a category into tbl_category (will fail if ID already exists).
      
      Args:
         category_id: Unique ID for the category
         category_name: Name of the category
         parent_category_id: ID of the parent category, None for top-level
      """
      sql = "INSERT INTO tbl_category (id, name, category, dateImport) VALUES (%s, %s, %s, NOW())"
      self.cursor.execute(sql, (category_id, category_name, parent_category_id))
