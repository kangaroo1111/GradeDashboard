from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Base class for all models
Base = declarative_base()


# Define the Responses table (association table between Student and Question)
Responses = Table('Responses', Base.metadata,
    Column('id', Integer, primary_key = True),
    Column('student', String, ForeignKey('Student.sid')),
    # Column('tag', String, ForeignKey('Question.tag')),
    Column('problem_type', String, ForeignKey('Question.problem_type')),
    Column('score', Integer),
    Column('assignment', String, ForeignKey('Question.assignment')),
    Column('quiz_number', Integer, ForeignKey('Question.quiz_number')),
    Column('option', Integer, ForeignKey('Question.option')),
    Column('subpart', String, ForeignKey('Question.subpart')),
    UniqueConstraint('student', 'assignment', 'quiz_number', 'option','subpart')
    )



# Define the Student table
class Student(Base):
    __tablename__ = 'Student'
    sid = Column(String, primary_key = True) #student id number
    name = Column(String)
    lecture = Column(String) #11am (0) or 12pm (1)
    answers = relationship('Question', secondary=Responses, backref='Student')

# Define the Question table
class Question(Base):
    __tablename__ = 'Question'
    id = Column(Integer, primary_key = True)
    # tag = Column(String) #problem type eg A1a, A4, etc
    assignment = Column(String) #midterm or Final or Quiz
    quiz_number = Column(Integer) #quiz number
    problem_type = Column(String) #problem_type
    option = Column(Integer) #question 1 or 2 on quiz
    subpart = Column(String) #part a, b, c, d, etc
    students = relationship('Student', secondary=Responses, backref='Question')

class Tag(Base):
    __tablename__='Tags'
    id = Column(Integer, primary_key = True)
    text = Column(String)

Question_Tags = Table('Question_Tags', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('text', String, ForeignKey('Tags.text')),
    Column('question', Integer, ForeignKey('Question.id'))
    )


# Define the ProcessedQuizzes table to track processed quizzes
class ProcessedQuizzes(Base):
    __tablename__ = 'ProcessedQuizzes'
    assignment = Column(String) #quiz or midterm
    quiz_id = Column(Integer, primary_key=True)  # Track quiz numbers processed
    lecture = Column(String) #which lecture is the quiz for
    process_date = Column(DateTime) #date of last modification


# Create a new SQLite database (or connect to an existing one)
engine = create_engine('sqlite:///student_grades.db')

# Create all tables in the database
Base.metadata.create_all(engine)

# Create a session to interact with the database
Session = sessionmaker(bind=engine)
session = Session()
