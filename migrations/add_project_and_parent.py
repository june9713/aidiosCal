from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, engine
from app.models.models import Schedule

def upgrade():
    # Create new columns
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE schedules ADD COLUMN project_name VARCHAR"))
        conn.execute(text("ALTER TABLE schedules ADD COLUMN parent_id INTEGER REFERENCES schedules(id)"))
        conn.commit()

def downgrade():
    # Remove new columns
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE schedules DROP COLUMN project_name"))
        conn.execute(text("ALTER TABLE schedules DROP COLUMN parent_id"))
        conn.commit()

if __name__ == "__main__":
    upgrade() 