from services.import_steps.base import ImportStep
from repositories.category_repository import CategoryRepository


class CategoriesStep(ImportStep):
   def name(self) -> str:
      return "categories"

   def run(self, data: dict, uow) -> bool:
      if not data or "categories" not in data:
         print("  No categories data found in YAML")
         return True
      
      repo = CategoryRepository(uow)
      inserted = 0
      updated = 0
      
      # Start ID counter from max existing ID + 1
      max_id = repo.get_max_category_id()
      category_id_counter = [max_id + 1]
      
      def insert_category_recursive(category_data, parent_id=None):
         """
         Recursively insert or update a category and all its subcategories.
         
         If category already exists (same name and parent), reuse its ID.
         Otherwise, assign a new ID and insert it.
         
         Args:
            category_data: Dictionary with 'name' and optional 'subcategories'
            parent_id: ID of the parent category, None for root categories
            
         Returns:
            Current category's ID for use as parent in subcategories
         """
         nonlocal inserted, updated
         
         category_name = category_data.get("name")
         if not category_name:
            return None
         
         # Check if category already exists
         existing_id = repo.get_category_id_by_name_and_parent(category_name, parent_id)
         
         if existing_id is not None:
            # Category exists, reuse its ID
            current_id = existing_id
            updated += 1
         else:
            # New category, assign new ID and insert
            current_id = category_id_counter[0]
            repo.insert_category(current_id, category_name, parent_id)
            inserted += 1
            category_id_counter[0] += 1
         
         # Process subcategories recursively
         subcategories = category_data.get("subcategories", [])
         if isinstance(subcategories, list):
            for subcategory_data in subcategories:
               if isinstance(subcategory_data, dict):
                  insert_category_recursive(subcategory_data, current_id)
         
         return current_id
      
      # Process all root categories
      for category_data in data["categories"]:
         if isinstance(category_data, dict):
            insert_category_recursive(category_data, None)
      
      print(f"  Inserted {inserted} new categories, {updated} existing categories recognized")
      return True
