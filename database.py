import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

project_path = os.path.dirname(os.path.abspath(__file__))
load_dotenv()

# mariaDB 연결

# db url 설정
database_url = f"mysql+pymysql://root:{os.environ.get("DB_PASSWORD")}@localhost:3306/WordSearch"

# Engine 생성
engine = create_engine(database_url, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

# 모델 정의
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False)
    password = Column(String(100), nullable=False)

class Answers(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    answer = Column(String(100), nullable=False)


if __name__ == "__main__":
    print(database_url)