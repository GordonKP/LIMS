from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from config.tables import Base  # Import your Base class that includes all table definitions
from config.config import CONNECTION_STRING

# Create an engine
engine = create_engine(CONNECTION_STRING, echo=True)  # Set echo=True for debugging SQL output

'''Drop all tables'''
#Base.metadata.drop_all(engine, checkfirst=True)  # Corrected drop_all() call

'''Drop a specific table'''
table = Base.metadata.tables.get('MetalsResults')
table.drop(engine, checkfirst=True)

Base.metadata.create_all(engine)

print("Database tables checked/created successfully.")