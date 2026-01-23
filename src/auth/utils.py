"""
Utility functions for authentication.
"""


def get_database_name(db_username: str, username_prefix: str = "finia_", database_prefix: str = "finiaDB_") -> str:
    """
    Leitet Datenbanknamen aus DB-Username ab.
    
    Pattern: finia_<Name> → finiaDB_<Name>
    
    Args:
        db_username: MySQL-Username (z.B. "finia_username")
        username_prefix: Erwartetes Präfix im Username
        database_prefix: Präfix für Datenbanknamen
        
    Returns:
        Datenbankname (z.B. "finiaDB_username")
        
    Raises:
        ValueError: Bei ungültigem Username-Format
        
    Beispiele:
        >>> get_database_name("finia_username")
        'finiaDB_username'
        >>> get_database_name("finia_alice")
        'finiaDB_alice'
    """
    if not db_username.startswith(username_prefix):
        raise ValueError(f"Username muss mit '{username_prefix}' beginnen")
    
    if len(db_username) <= len(username_prefix):
        raise ValueError("Username zu kurz")
    
    # Suffix extrahieren (z.B. "username" aus "finia_username")
    suffix = db_username[len(username_prefix):]
    
    # Nur alphanumerische Zeichen + Underscore erlauben
    if not suffix.replace("_", "").isalnum():
        raise ValueError("Ungültige Zeichen im Username")
    
    return f"{database_prefix}{suffix}"
