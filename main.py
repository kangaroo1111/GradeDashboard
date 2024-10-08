from flask import Flask, url_for, request, render_template, send_file, jsonify, session, g, redirect
from markupsafe import escape, Markup
import os
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import io
from dashboard import db
import base64
import seaborn as sns
from functools import wraps



app = Flask(__name__)


app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE='C:\grade_dash\grade_database\student_grades.db',
)

# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

#login

@app.route("/", methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None

        if username != 'kayla':
            error = 'Incorrect username.'
        elif not password == 'reardon':
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = 'Kayla'
            return redirect(url_for('hello_world'))

        flash(error)

    return render_template('login.html')


@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = user_id

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('login'))

        return view(**kwargs)

    return wrapped_view

#end login

@app.route("/home")
@login_required #make sure logged in
def hello_world():
    db_connection = db.get_db()
    # cursor = db_connection.execute('SELECT lecture FROM Student')
    # data = [dict(row) for row in cursor.fetchall()]
    data = ["11am", "12pm"]
    return render_template('home.html', lectures=data)

@app.route("/change_me", methods=['POST'])
@login_required  #make sure logged in
def change_me():
    vars = request.form['time']
    print(vars)
    #TODO use data from vars to query db
    db_connection = db.get_db()
    cursor = db_connection.execute('SELECT name FROM Student WHERE lecture = ?', (vars,))
    st_data = [st['name'] for st in [dict(row) for row in cursor.fetchall()]] + ["overall"]
    lec_data = ["11am", "12pm"]
    cursor = db_connection.execute('SELECT quiz_id FROM ProcessedQuizzes WHERE assignment = "Quiz"')
    wk_data = [dict(row) for row in cursor.fetchall()] + ["overall"]
    # print(data)
    #TODO change to render hud with data from db
    return render_template('hud.html', student='overall', week='overall', lectures=lec_data, students=st_data, weeks=wk_data, graphs={}, selected_time=vars, selected_student="overall", selected_week="overall")

@app.route("/hud", methods=['GET','POST'])
@login_required  #make sure logged in
def hud():
    time_var = request.form['time']
    student_var = request.form['student']
    week_var = request.form['week']
    db_connection = db.get_db()
    cursor = db_connection.execute('SELECT name FROM Student WHERE lecture = ?', (time_var,))
    st_data = [st['name'] for st in [dict(row) for row in cursor.fetchall()]] + ["overall"]
    lec_data = ["11am", "12pm"]
    cursor = db_connection.execute('SELECT quiz_id FROM ProcessedQuizzes WHERE assignment = "Quiz"')
    wk_data = [dict(row) for row in cursor.fetchall()] + ["overall"]

    graphs = {}

    if student_var == 'overall':
        # 1. Score Over Time graph
        query = """
        WITH MaxScores AS (
        -- Step 1: Calculate sum of scores for each tuple (assignment, quiz_number, option, problem_type) for the specific student
        SELECT
        r.assignment,
        r.quiz_number,
        r.option,
        r.problem_type,
        SUM(r.score) AS total_score
        FROM Responses r
        GROUP BY r.assignment, r.quiz_number, r.option, r.problem_type
        ),
        -- Step 2: Find the max score for each (assignment, quiz_number, problem_type) for the student
        MaxValues AS (
        SELECT
        assignment,
        quiz_number,
        problem_type,
        MAX(total_score) AS max_score
        FROM MaxScores
        GROUP BY assignment, quiz_number, problem_type
        )
        SELECT
        problem_type,
        AVG(mv.max_score) AS type_avg
        FROM MaxValues mv
        GROUP BY problem_type;
        """
        ptype_df = pd.read_sql_query(query, db_connection)
        if not ptype_df.empty:
            ptype_df.fillna(0, inplace=True)
            plt.figure(figsize=(10, 6))
            plt.bar(ptype_df['problem_type'], ptype_df['type_avg'], color='orange')
            plt.xlabel('Problem Type')
            plt.ylabel('Average Max Score')
            plt.title(f'Max Scores by Problem Type')
            plt.xticks(rotation=45)
            plt.ylim(0, ptype_df['type_avg'].max() + 10)

            ptype_graph = io.BytesIO()
            plt.savefig(ptype_graph, format='png')
            plt.close()
            ptype_graph.seek(0)
            graphs['Problem_Type_Averages'] = base64.b64encode(ptype_graph.getvalue()).decode('utf-8')


        # 3. Attendance vs Scores graph
        query = """
        WITH MaxScores AS (
        -- Step 1: Calculate sum of scores for each tuple (assignment, quiz_number, option, problem_type) for the specific student
        SELECT
        r.assignment,
        r.quiz_number,
        r.option,
        r.problem_type,
        SUM(r.score) AS total_score
        FROM Responses r
        GROUP BY r.assignment, r.quiz_number, r.option, r.problem_type
        ),
        -- Step 2: Find the max score for each (assignment, quiz_number, problem_type) for the student
        MaxValues AS (
        SELECT
        assignment,
        quiz_number,
        problem_type,
        MAX(total_score) AS max_score
        FROM MaxScores
        GROUP BY assignment, quiz_number, problem_type
        ),
        -- Step 3: Select the tuples that achieve the max score for the student
        MaxTuples AS (
        SELECT
        ms.assignment,
        ms.quiz_number,
        ms.option,
        ms.problem_type,
        ms.total_score
        FROM MaxScores ms
        INNER JOIN MaxValues mv
        ON ms.assignment = mv.assignment
        AND ms.quiz_number = mv.quiz_number
        AND ms.problem_type = mv.problem_type
        AND ms.total_score = mv.max_score
        ),
        -- Step 4: Join MaxTuples with Responses to get corresponding subparts for the student
        MaxResponses AS (
        SELECT
        r.assignment,
        r.quiz_number,
        r.option,
        r.problem_type,
        r.subpart,
        r.score
        FROM Responses r
        INNER JOIN MaxTuples mt
        ON r.assignment = mt.assignment
        AND r.quiz_number = mt.quiz_number
        AND r.option = mt.option
        AND r.problem_type = mt.problem_type
        ),
        -- Step 5: Get the question ID from the Question table for each tuple in MaxResponses
        MaxQuestions AS (
        SELECT
        mr.assignment,
        mr.quiz_number,
        mr.option,
        mr.problem_type,
        mr.subpart,
        mr.score,
        q.id AS question_id
        FROM MaxResponses mr
        INNER JOIN Question q
        ON mr.assignment = q.assignment
        AND mr.quiz_number = q.quiz_number
        AND mr.option = q.option
        AND mr.subpart = q.subpart
        )
        -- Step 6: Join with Question_Tags to get the tags associated with the question IDs
        SELECT
        t.text AS tag,
        AVG(mq.score) AS avg_score
        FROM MaxQuestions mq
        INNER JOIN Question_Tags qt
        ON mq.question_id = qt.question -- Use question_id to join with Question_Tags
        INNER JOIN Tags t
        ON qt.text = t.text
        GROUP BY t.text;
        """
        tags_df=pd.read_sql_query(query, db_connection)


        if not tags_df.empty:
            tags_df.fillna(0, inplace=True)
            plt.figure(figsize=(10, 6))
            plt.bar(tags_df['tag'], tags_df['avg_score'], color='orange')
            plt.xlabel('Tag')
            plt.ylabel('Average Score')
            plt.title(f'Performance by Tag')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.ylim(0, tags_df['avg_score'].max() + 1)

            tags_graph = io.BytesIO()
            plt.savefig(tags_graph, format='png')
            plt.close()
            tags_graph.seek(0)
            graphs['Scores_by_Tag'] = base64.b64encode(tags_graph.getvalue()).decode('utf-8')

            # Send the graphs to the template
            return render_template('hud.html', student=student_var, week=week_var, lectures=lec_data, students=st_data, weeks=wk_data, graphs=graphs, selected_time=time_var, selected_student=student_var, selected_week=week_var)

    else:
        # 1. Score Over Time graph
        query = """
        SELECT
        problem_type,
        MAX(total_score) AS max_score
        FROM (
        SELECT
        problem_type,
        option,
        quiz_number,  -- Include quiz_number in the grouping
        SUM(score) AS total_score
        FROM Responses
        WHERE student = ?
        GROUP BY problem_type, option, quiz_number
        ) AS option_totals
        GROUP BY problem_type;
        """
        ptype_df = pd.read_sql_query(query, db_connection, params=(student_var,))
        if not ptype_df.empty:
            ptype_df.fillna(0, inplace=True)
            plt.figure(figsize=(10, 8))
            plt.bar(ptype_df['problem_type'], ptype_df['max_score'], color='orange')
            plt.xlabel('Problem Type')
            plt.ylabel('Max Score')
            plt.title(f'Max Scores by Problem Type for Student {student_var}')
            plt.xticks(rotation=45)
            plt.ylim(0, ptype_df['max_score'].max() + 2)

            ptype_graph = io.BytesIO()
            plt.savefig(ptype_graph, format='png')
            plt.close()
            ptype_graph.seek(0)
            graphs['Score_by_Problem_Type'] = base64.b64encode(ptype_graph.getvalue()).decode('utf-8')

        # 2. Quiz Performance graph
        query = """
        WITH ScoreSums AS (
        SELECT
        r.quiz_number,
        r.option,
        SUM(r.score) AS total_score
        FROM Responses r
        WHERE r.student = :student_id -- Replace :student_id with the specific student's ID
        GROUP BY r.quiz_number, r.option
        )
        SELECT
        quiz_number,
        option,
        total_score
        FROM ScoreSums
        ORDER BY quiz_number, option;
        """
        quiz_df = pd.read_sql_query(query, db_connection, params=(student_var,))
        if not quiz_df.empty:
            quiz_df.fillna(0, inplace=True)
            # Create a bar plot
            plt.figure(figsize=(10, 8))
            sns.barplot(data=quiz_df, x='quiz_number', y='total_score', hue='option', palette='viridis')

            # Set title and labels
            plt.title('Total Scores by Quiz and Option for Student', fontsize=16)
            plt.xlabel('Quiz Number', fontsize=14)
            plt.ylabel('Total Score', fontsize=14)
            plt.legend(title='Option', fontsize=12)
            plt.xticks(rotation=0)
            plt.tight_layout()

            quiz_graph = io.BytesIO()
            plt.savefig(quiz_graph, format='png')
            plt.close()
            quiz_graph.seek(0)
            graphs['Quiz_Performance'] = base64.b64encode(quiz_graph.getvalue()).decode('utf-8')

        # 3. Average Tag Scores graph
        query = '''
        WITH MaxScores AS (
        -- Step 1: Calculate sum of scores for each tuple (assignment, quiz_number, option, problem_type) for the specific student
        SELECT
        r.assignment,
        r.quiz_number,
        r.option,
        r.problem_type,
        SUM(r.score) AS total_score
        FROM Responses r
        WHERE r.student = :student_id -- Specify the student ID directly in Responses
        GROUP BY r.assignment, r.quiz_number, r.option, r.problem_type
        ),
        -- Step 2: Find the max score for each (assignment, quiz_number, problem_type) for the student
        MaxValues AS (
        SELECT
        assignment,
        quiz_number,
        problem_type,
        MAX(total_score) AS max_score
        FROM MaxScores
        GROUP BY assignment, quiz_number, problem_type
        ),
        -- Step 3: Select the tuples that achieve the max score for the student
        MaxTuples AS (
        SELECT
        ms.assignment,
        ms.quiz_number,
        ms.option,
        ms.problem_type,
        ms.total_score
        FROM MaxScores ms
        INNER JOIN MaxValues mv
        ON ms.assignment = mv.assignment
        AND ms.quiz_number = mv.quiz_number
        AND ms.problem_type = mv.problem_type
        AND ms.total_score = mv.max_score
        ),
        -- Step 4: Join MaxTuples with Responses to get corresponding subparts for the student
        MaxResponses AS (
        SELECT
        r.assignment,
        r.quiz_number,
        r.option,
        r.problem_type,
        r.subpart,
        r.score
        FROM Responses r
        INNER JOIN MaxTuples mt
        ON r.assignment = mt.assignment
        AND r.quiz_number = mt.quiz_number
        AND r.option = mt.option
        AND r.problem_type = mt.problem_type
        WHERE r.student = :student_id -- Filter by the specific student
        ),
        -- Step 5: Get the question ID from the Question table for each tuple in MaxResponses
        MaxQuestions AS (
        SELECT
        mr.assignment,
        mr.quiz_number,
        mr.option,
        mr.problem_type,
        mr.subpart,
        mr.score,
        q.id AS question_id
        FROM MaxResponses mr
        INNER JOIN Question q
        ON mr.assignment = q.assignment
        AND mr.quiz_number = q.quiz_number
        AND mr.option = q.option
        AND mr.subpart = q.subpart
        )
        -- Step 6: Join with Question_Tags to get the tags associated with the question IDs
        SELECT
        t.text AS tag,
        AVG(mq.score) AS avg_score
        FROM MaxQuestions mq
        INNER JOIN Question_Tags qt
        ON mq.question_id = qt.question -- Use question_id to join with Question_Tags
        INNER JOIN Tags t
        ON qt.text = t.text
        GROUP BY t.text;
        '''
        tags_df=pd.read_sql_query(query, db_connection, params=(student_var,))


        if not tags_df.empty:
            tags_df.fillna(0, inplace=True)
            plt.figure(figsize=(15, 15))
            plt.bar(tags_df['tag'], tags_df['avg_score'], color='orange')
            plt.xlabel('Tag')
            plt.ylabel('Average Score')
            plt.title(f'Performance by Tag for {student_var}')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.ylim(0, tags_df['avg_score'].max() + 1)

            tags_graph = io.BytesIO()
            plt.savefig(tags_graph, format='png')
            plt.close()
            tags_graph.seek(0)
            graphs['Scores_by_Tag'] = base64.b64encode(tags_graph.getvalue()).decode('utf-8')
        # Send the graphs to the template
        return render_template('hud.html', student=student_var, week=week_var, lectures=lec_data, students=st_data, weeks=wk_data, graphs=graphs, selected_time=time_var, selected_student=student_var, selected_week=week_var)

@app.route("/get_students", methods=['GET'])
def get_students():
    time_var = request.args.get('time')
    db_connection = db.get_db()
    cursor = db_connection.execute('SELECT name FROM Student WHERE lecture = ?', (time_var,))
    st_data = [st['name'] for st in [dict(row) for row in cursor.fetchall()]]

    return jsonify({'students': st_data})



@app.template_filter('b64encode')
def b64encode_filter(data):
    return Markup(base64.b64encode(data.read()).decode('utf-8'))


if __name__ == '__main__':
    app.run()
