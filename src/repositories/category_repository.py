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
         name: Category name (can be simple name or full hierarchical name)

      Returns:
         Category ID if found, None otherwise
      """
      # First try to find by simple name in tbl_category
      sql = "SELECT id FROM tbl_category WHERE name = %s"
      self.cursor.execute(sql, (name,))
      result = self.cursor.fetchone()
      if result:
         return result[0]
      
      # If not found, try to find by full name in view_categoryFullname
      sql = "SELECT id FROM view_categoryFullname WHERE fullname = %s"
      self.cursor.execute(sql, (name,))
      result = self.cursor.fetchone()
      if result:
         return result[0]

      # Fallback: resolve hierarchy directly from tbl_category if view is incomplete
      return self._find_category_by_hierarchical_name(name)

   def _find_category_by_hierarchical_name(self, fullname: str) -> int:
      """
      Resolve a category ID by traversing tbl_category using a hierarchical name.

      Args:
         fullname: Full hierarchical name ("Parent - Child - Subchild")

      Returns:
         Category ID if found, None otherwise
      """
      parts = [p.strip() for p in fullname.split(' - ') if p.strip()]
      if not parts:
         return None

      parent_id = None
      current_id = None
      for part in parts:
         sql = "SELECT id FROM tbl_category WHERE name = %s AND category <=> %s"
         self.cursor.execute(sql, (part, parent_id))
         row = self.cursor.fetchone()
         if not row:
            return None
         current_id = row[0]
         parent_id = current_id

      return current_id

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
      Get all categories with their full hierarchical names from view_categoryFullname (legacy: returns all).
      
      Returns:
         List of dicts with 'id', 'name', and 'fullname' keys
      """
      return self.get_all_fullnames_paginated(page=1, page_size=1000000)['categories']

   def get_all_fullnames_paginated(self, page: int = 1, page_size: int = 100) -> dict:
      """
      Get paginated categories with their full hierarchical names from view_categoryFullname.
      
      Args:
         page: Page number (1-based)
         page_size: Number of records per page (max 1000)

      Returns:
         Dict with 'categories' list, 'page', 'page_size', and 'total' count
      """
      page = max(1, page)
      page_size = min(max(1, page_size), 1000)
      offset = (page - 1) * page_size
      
      # Get total count
      count_sql = "SELECT COUNT(*) FROM view_categoryFullname"
      self.cursor.execute(count_sql)
      total = self.cursor.fetchone()[0]
      
      # Get paginated data
      sql = "SELECT id, name, fullname FROM view_categoryFullname ORDER BY fullname LIMIT %s OFFSET %s"
      self.cursor.execute(sql, (page_size, offset))
      results = self.cursor.fetchall()
      
      categories = [
         {
            'id': row[0],
            'name': row[1],
            'fullname': row[2]
         }
         for row in results
      ]
      
      return {
         'categories': categories,
         'page': page,
         'page_size': page_size,
         'total': total
      }

   def get_all_with_parent(self) -> list[dict]:
      """
      Get all categories with their parent category information (legacy: returns all).
      
      Returns:
         List of dicts with 'id', 'name', and 'parent_id' keys
      """
      return self.get_all_with_parent_paginated(page=1, page_size=1000000)['categories']

   def get_all_with_parent_paginated(self, page: int = 1, page_size: int = 100) -> dict:
      """
      Get paginated categories with their parent category information.
      
      Args:
         page: Page number (1-based)
         page_size: Number of records per page (max 1000)

      Returns:
         Dict with 'categories' list, 'page', 'page_size', and 'total' count
      """
      page = max(1, page)
      page_size = min(max(1, page_size), 1000)
      offset = (page - 1) * page_size
      
      # Get total count
      count_sql = "SELECT COUNT(*) FROM tbl_category"
      self.cursor.execute(count_sql)
      total = self.cursor.fetchone()[0]
      
      # Get paginated data
      sql = "SELECT id, name, category FROM tbl_category ORDER BY name LIMIT %s OFFSET %s"
      self.cursor.execute(sql, (page_size, offset))
      results = self.cursor.fetchall()
      
      categories = [
         {
            'id': row[0],
            'name': row[1],
            'parent_id': row[2]
         }
         for row in results
      ]
      
      return {
         'categories': categories,
         'page': page,
         'page_size': page_size,
         'total': total
      }

   def get_all_with_parent_unpaginated(self) -> list:
      """
      Get ALL categories with their parent category information (efficient single query).
      
      Returns:
         List of category dictionaries with id, name, parent_id
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
