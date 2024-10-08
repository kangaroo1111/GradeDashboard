from sqlalchemy import create_engine, text

# Connect to the database using SQLAlchemy
engine = create_engine('sqlite:///C://grade_database//student_grades.db')

# Run the PRAGMA command
with engine.connect() as conn:
    result = conn.execute(text('PRAGMA table_info(ProcessedQuizzes);'))
    for row in result:
        print(row)

with engine.connect() as conn:
    result = conn.execute(text('SELECT * FROM ProcessedQuizzes;'))
    for row in result:
        print(row)

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM Responses WHERE student = 'Trisha Prasanna' AND quiz_number = 5"))
    for row in result:
        print(row)
