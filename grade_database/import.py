import os
import pandas as pd
import sqlite3
from datetime import datetime
import numpy as np

# Connect to your SQLite database
conn = sqlite3.connect('student_grades.db')

# Folder containing all quiz evaluation folders
course_folder = r'C:\Users\sanat\Documents\Math_118_Fall_2024'

problem_type_list = ['F', 'A1a', 'A2a', 'A3a', 'A4','A5', 'A6', 'A7', 'A8', 'A9', 'A1b', 'A2b', 'A3b', 'A10', 'A11']

def cap(a_list, b_list):
    i=0
    while i in range(len(a_list)):
        if a_list[i] in b_list:
            return a_list[i]
        else:
            i+=1
    return a_list[-1]

# Loop through each quiz folder inside the 'Course' folder
for quiz_folder in os.listdir(course_folder):
    if not quiz_folder.startswith('Math_118_') or not os.path.isdir(os.path.join(course_folder, quiz_folder)):
        continue  # Skip files or folders that don't match the pattern


    # Extract the quiz number from the folder name
    assignment = quiz_folder.split('_')[-2]
    quiz_number = int(quiz_folder.split('_')[-1])
    lecture = quiz_folder.split('_')[2]
    last_mod = datetime.fromtimestamp(os.path.getmtime(os.path.join(course_folder, quiz_folder)))

    print(assignment, quiz_number, lecture, last_mod)


    # Check if this quiz has already been processed
    cursor = conn.execute('SELECT process_date FROM ProcessedQuizzes WHERE assignment = ? and quiz_id = ? and lecture = ?', (assignment, quiz_number, lecture))
    p_time = cursor.fetchall()
    print(p_time)
    if p_time != []:
        if datetime.strptime(p_time[0][0], "%Y-%m-%d %H:%M:%S.%f") < last_mod:
            ans = input(f"Grades for {assignment} {quiz_number} for lecture {lecture} have been changed. Update? Y/N")
            if ans == "Y":
                time =  datetime.now()
                conn.execute('''
                    UPDATE ProcessedQuizzes
                    SET process_date = ?
                    WHERE quiz_id = ? and assignment = ?
                ''', (time, quiz_number, assignment))
                conn.commit()
            if ans == "N":
                print(f"{assignment} {quiz_number} has already been processed. Skipping...")
                continue  # Skip this quiz as it's already been processed

    quiz_folder = os.path.join(course_folder, quiz_folder)


    # Process CSV files in the question folder
    for csv_file in os.listdir(quiz_folder):
        if csv_file.endswith('.csv'):
            # Extract the option (question number) from the file name (e.g., "1_1.csv")
            if len(csv_file.split('_')) < 2 or len(csv_file.split('_')[1].split('.')) == 0:
                subpart = 'a'
            else:
                subpart = csv_file.split('_')[1].split('.')[0]
            print(subpart)
            option = int(csv_file[0])

            # Read the CSV file into a pandas DataFrame
            csv_path = os.path.join(quiz_folder, csv_file)
            df = pd.read_csv(csv_path)

            # tag = df['Tags'].iloc[0]

            # Insert the question into the Question table (if not already present)
            question_data = (assignment, quiz_number, option, subpart)
            print(question_data)
            conn.execute('''
                INSERT OR IGNORE INTO Question (assignment, quiz_number, option, subpart)
                VALUES (?, ?, ?, ?)
            ''', question_data)
            conn.commit()

            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_unique_question';")
            index_exists = cursor.fetchone()

            if not index_exists:
                conn.execute('''
                CREATE UNIQUE INDEX idx_unique_question ON Question (assignment, quiz_number, option, subpart);
                ''')
                conn.commit()

            # Loop over each row (each student) in the DataFrame
            for _, row in df.iterrows():
                student_name = str(row['First Name']) + ' ' + str(row['Last Name'])
                student_sid = str(row['SID'])
                student_score = row['Score']
                # tag = row['Tags']
                # problem_type = row.iloc[-1]
                #print(tag)
                if isinstance(row['Tags'], str):
                    if row['Tags'].lower() == 'nan':
                        problem_type = 'None'
                        tags = 'None'
                    else:
                        tag_list = row['Tags'].split('; ')
                        problem_type = cap(tag_list, problem_type_list)
                        tags = tag_list.remove(problem_type)
                else:
                    problem_type = 'None'
                    tags = 'None'

                # Insert student into the Student table (if not already present)
                student_data = (student_sid, student_name, lecture)
                conn.execute('''
                    INSERT OR IGNORE INTO Student (sid, name, lecture)
                    VALUES (?, ?, ?)
                ''', student_data)

                #Insert tags for the question into Question table
                conn.execute('''
                    UPDATE Question
                    SET problem_type = ?
                    WHERE assignment = ? and quiz_number = ? and option = ? and subpart = ?
                ''', (problem_type, assignment, quiz_number, option, subpart))

                # Insert the student's score for the current question into the Responses table
                response_data = (student_name, assignment, problem_type, quiz_number, option, subpart, student_score)
                conn.execute('''
                    INSERT INTO Responses (student, assignment, problem_type, quiz_number, option, subpart, score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student, assignment, quiz_number, option, subpart) DO UPDATE SET SCORE = excluded.score;
                ''', response_data)

                cursor = conn.execute('''
                    SELECT id FROM Question
                    WHERE assignment = ? and quiz_number = ? and option = ? and subpart = ?
                ''', (assignment, quiz_number, option, subpart))
                id_row = cursor.fetchall()
                current_id = id_row[0][0]

                tag_tuples = [(tag,) for tag in tag_list]
                query_tag = """ INSERT OR IGNORE INTO Tags (text) VALUES (?)"""
                cursor.executemany(query_tag, tag_tuples)


                values = [(tag, current_id) for tag in tag_list]
                query = """INSERT OR IGNORE INTO Question_Tags (text, question) VALUES (?, ?)"""
                cursor.executemany(query, values)

            # Commit after processing each CSV file
            conn.commit()

    # After processing the quiz, mark it as processed
    process_date_str = datetime.now()
    conn.execute('INSERT OR IGNORE INTO ProcessedQuizzes (quiz_id, assignment, process_date, lecture) VALUES (?, ?, ?, ?)', (quiz_number, assignment, process_date_str, lecture))
    conn.commit()

# Close the connection
conn.close()
