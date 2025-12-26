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

   def get_all_fullnames(self) -> list[dict]:
      """
      Get all categories with their full hierarchical names from view_categoryFullname.
      
      Returns:
         List of dicts with 'id', 'name', and 'fullname' keys
      """
      sql = "SELECT id, name, fullname FROM view_categoryFullname ORDER BY fullname"
      self.cursor.execute(sql)
      results = self.cursor.fetchall()
      return [
         {
            'id': row[0],
            'name': row[1],
            'fullname': row[2]
         }
         for row in results
      ]

   def get_all_with_parent(self) -> list[dict]:
      """
      Get all categories with their parent category information.
      
      Returns:
         List of dicts with 'id', 'name', and 'parent_id' keys
      """
      sql = "SELECT id, name, category FROM tbl_category ORDER BY name"
      self.cursor.execute(sql)
      results = self.cursor.fetchall()
      return [
         {
            'id': row[0],
            'name': row[1],
            'parent_id': row[2]
         }
         for row in results
      ]

   def update_category(self, category_id: int, new_name: str, parent_category_id: int = None) -> bool:
      """
      Update a category's name and/or parent.
      
      Args:
         category_id: ID of the category to update
         new_name: New name for the category
         parent_category_id: New parent category ID (None for top-level)
         
      Returns:
         True if update was successful, False otherwise
      """
      sql = "UPDATE tbl_category SET name = %s, category = %s WHERE id = %s"
      self.cursor.execute(sql, (new_name, parent_category_id, category_id))
      return self.cursor.rowcount > 0

   def delete_category(self, category_id: int) -> bool:
      """
      Delete a category and reassign its children to its parent.
      
      Args:
         category_id: ID of the category to delete
         
      Returns:
         True if deletion was successful, False otherwise
      """
      # First get the parent of the category to be deleted
      sql = "SELECT category FROM tbl_category WHERE id = %s"
      self.cursor.execute(sql, (category_id,))
      result = self.cursor.fetchone()
      parent_id = result[0] if result else None
      
      # Move children to the deleted category's parent
      sql = "UPDATE tbl_category SET category = %s WHERE category = %s"
      self.cursor.execute(sql, (parent_id, category_id))
      
      # Delete the category
      sql = "DELETE FROM tbl_category WHERE id = %s"
      self.cursor.execute(sql, (category_id,))
      return self.cursor.rowcount > 0

   def get_category_by_id(self, category_id: int) -> dict:
      """
      Get a single category by ID.
      
      Args:
         category_id: ID of the category
         
      Returns:
         Dict with 'id', 'name', and 'parent_id' keys, or None if not found
      """
      sql = "SELECT id, name, category FROM tbl_category WHERE id = %s"
      self.cursor.execute(sql, (category_id,))
      result = self.cursor.fetchone()
      if result:
         return {
            'id': result[0],
            'name': result[1],
            'parent_id': result[2]
         }
      return None
