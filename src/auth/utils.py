"""
Utility functions for authentication.
"""


def get_database_name(db_username: str, username_prefix: str = "finia_", database_prefix: str = "finiaDB_") -> str:
    """
    Leitet Datenbanknamen aus DB-Username ab.
    
    Pattern: finia_<Name> → finiaDB_<Name>
    
    Args:
        db_username: MySQL-Username (z.B. "finia_Markus")
        username_prefix: Erwartetes Präfix im Username
        database_prefix: Präfix für Datenbanknamen
        
    Returns:
        Datenbankname (z.B. "finiaDB_Markus")
        
    Raises:
        ValueError: Bei ungültigem Username-Format
        
    Beispiele:
        >>> get_database_name("finia_Markus")
        'finiaDB_Markus'
        >>> get_database_name("finia_Anna")
        'finiaDB_Anna'
    """
    if not db_username.startswith(username_prefix):
        raise ValueError(f"Username muss mit '{username_prefix}' beginnen")
    
    if len(db_username) <= len(username_prefix):
        raise ValueError("Username zu kurz")
    
    # Suffix extrahieren (z.B. "Markus" aus "finia_Markus")
    suffix = db_username[len(username_prefix):]
    
    # Nur alphanumerische Zeichen + Underscore erlauben
    if not suffix.replace("_", "").isalnum():
        raise ValueError("Ungültige Zeichen im Username")
    
    return f"{database_prefix}{suffix}"
