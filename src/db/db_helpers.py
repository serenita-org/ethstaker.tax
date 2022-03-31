import os


def get_db_uri():
    db_uri = os.getenv("DB_URI")
    if db_uri is None or db_uri == "":
        raise ValueError("DB_URI is not defined")
    return db_uri
