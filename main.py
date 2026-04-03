from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, text
from types import SimpleNamespace
from script import DBMaker as make_db

sql_user = "root"
sql_pass = "cset155"
sql_server = "localhost"
sql_db_name = "testapp"

try:
    if not make_db.db_exists(sql_user, sql_pass, sql_server, sql_db_name):
        make_db.create_db(sql_user, sql_pass, sql_server, sql_db_name)
except Exception as e:
    print(e)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'devkey'

connection_str = f"mysql://{sql_user}:{sql_pass}@{sql_server}/{sql_db_name}"
engine = create_engine(connection_str, echo=True)

def get_all_users():
    query = text("""
        SELECT acct_id, name, is_teacher
        FROM accounts
        ORDER BY acct_id
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    users = []
    for row in rows:
        users.append(SimpleNamespace(
            id=row["acct_id"],
            name=row["name"],
            role="teacher" if row["is_teacher"] else "student"
        ))
    return users

def get_user(acct_id):
    query = text("""
        SELECT acct_id, name, is_teacher
        FROM accounts
        WHERE acct_id = :acct_id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"acct_id": acct_id}).mappings().first()

    if not row:
        return None

    return SimpleNamespace(
        id=row["acct_id"],
        name=row["name"],
        role="teacher" if row["is_teacher"] else "student"
    )

def get_students():
    query = text("""
        SELECT acct_id, name
        FROM accounts
        WHERE is_teacher = FALSE
        ORDER BY acct_id
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    students = []
    for row in rows:
        students.append(SimpleNamespace(
            id=row["acct_id"],
            name=row["name"],
            role="student"
        ))
    return students

def get_teachers():
    query = text("""
        SELECT acct_id, name
        FROM accounts
        WHERE is_teacher = TRUE
        ORDER BY acct_id
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    teachers = []
    for row in rows:
        teachers.append(SimpleNamespace(
            id=row["acct_id"],
            name=row["name"],
            role="teacher"
        ))
    return teachers

def get_person(person_id):
    query = text("""
        SELECT acct_id, name
        FROM accounts
        WHERE acct_id = :person_id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"person_id": person_id}).mappings().first()

    return row.all() if row else None

def get_all_tests():
    query = text("""
        SELECT t.test_id, t.title, t.teacher_id, a.name AS teacher_name
        FROM tests t
        LEFT JOIN accounts a ON t.teacher_id = a.acct_id
        ORDER BY t.test_id DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    tests = []
    for row in rows:
        teacher = SimpleNamespace(
            id=row["teacher_id"],
            name=row["teacher_name"],
            role="teacher"
        ) if row["teacher_id"] else None

        tests.append(SimpleNamespace(
            id=row["test_id"],
            title=row["title"],
            teacher_id=row["teacher_id"],
            teacher=teacher
        ))
    return tests

def get_test_obj(test_id):
    query = text("""
        SELECT t.test_id, t.title, t.teacher_id, a.name AS teacher_name
        FROM tests t
        LEFT JOIN accounts a ON t.teacher_id = a.acct_id
        WHERE t.test_id = :test_id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"test_id": test_id}).mappings().first()

    if not row:
        return None

    teacher = SimpleNamespace(
        id=row["teacher_id"],
        name=row["teacher_name"],
        role="teacher"
    ) if row["teacher_id"] else None

    return SimpleNamespace(
        id=row["test_id"],
        title=row["title"],
        teacher_id=row["teacher_id"],
        teacher=teacher
    )

def get_questions_for_test(test_id):
    query = text("""
        SELECT test_id, q_number, q_txt
        FROM questions
        WHERE test_id = :test_id
        ORDER BY q_number
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"test_id": test_id}).mappings().all()

    questions = []
    for row in rows:
        questions.append(SimpleNamespace(
            id=row["q_number"],      # use q_number as the id in templates
            test_id=row["test_id"],
            q_number=row["q_number"],
            text=row["q_txt"]
        ))
    return questions

def get_responses_for_test(test_id):
    query = text("""
        SELECT r.response_id, r.student_id, r.submitted_at, r.grade, a.name AS student_name
        FROM responses r
        LEFT JOIN accounts a ON r.student_id = a.acct_id
        WHERE r.test_id = :test_id
        ORDER BY r.submitted_at DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"test_id": test_id}).mappings().all()

    responses = []
    for row in rows:
        student = SimpleNamespace(
            id=row["student_id"],
            name=row["student_name"],
            role="student"
        ) if row["student_id"] else None

        responses.append(SimpleNamespace(
            id=row["response_id"],
            test_id=test_id,
            student_id=row["student_id"],
            student=student,
            submitted_at=row["submitted_at"],
            grade=row["grade"]
        ))
    return responses

def get_answers_for(test_id, student_id):
    query = text("""
        SELECT a.test_id, a.q_number, a.answer
        FROM answers a
        WHERE a.test_id = :test_id AND a.student_id = :student_id
        ORDER BY a.q_number
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"test_id": test_id, "student_id": student_id}).mappings().all()

    answers = []
    for row in rows:
        answers.append(SimpleNamespace(
            test_id=row["test_id"],
            q_number=row["q_number"],
            answer=row["answer"]
        ))
    return answers


def get_grade_for(test_id, student_id):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT grade
                FROM grades
                WHERE test_id = :test_id AND student_id = :student_id
            """),
            {"test_id": test_id, "student_id": student_id}
        ).mappings().first()
    return row['grade'] if row else None

def get_question(question_id):
    query = text("""
        SELECT test_id, q_number, q_txt
        FROM questions
        WHERE q_number = :question_id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"question_id": question_id}).mappings().first()

    if not row:
        return None

    return SimpleNamespace(
        id=row["q_number"],
        test_id=row["test_id"],
        q_number=row["q_number"],
        text=row["q_txt"]
    )


def calculate_grade(response):
    return response.grade if hasattr(response, 'grade') else "Ungraded"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        role = request.form.get('role')

        if not name or not role:
            flash('Name and role are required.', 'error')
            return redirect(url_for('register'))

        user = User(name=name, role=role)
        db.session.add(user)
        db.session.commit()
        flash(f'{role.title()} registered successfully.', 'success')
        return redirect(url_for('accounts'))

    return render_template('register.html')


@app.route('/accounts')
def accounts():
    role = request.args.get('role', 'all')
    all_users = get_all_users()

    if role in ['student', 'teacher']:
        users = [u for u in all_users if u.role == role]
    else:
        users = all_users
        role = 'all'

    return render_template('accounts.html', users=users, selected_role=role)

@app.route('/tests')
def tests():
    tests = get_all_tests()
    return render_template('tests.html', tests=tests)


@app.route('/tests/create', methods=['GET', 'POST'])
def create_test():
    teachers = [u for u in get_all_users() if u.role == 'teacher']

    if request.method == 'POST':
        title = request.form.get('title').strip()
        teacher_id = request.form.get('teacher_id')

        if not title or not teacher_id:
            flash('Test title and teacher are required.', 'error')
            return redirect(url_for('create_test'))

        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO tests(title, teacher_id) VALUES(:title, :teacher_id)"),
                {"title": title, "teacher_id": int(teacher_id)}
            )
            conn.commit()

        flash('Test created successfully.', 'success')
        return redirect(url_for('tests'))

    return render_template('test_form.html', mode='create', teachers=teachers)


@app.route('/tests/<int:test_id>/edit', methods=['GET', 'POST'])
def edit_test(test_id):
    test=get_test_obj(test_id)
    if not test:
        flash('Test not found.', 'error')
        return redirect(url_for('tests'))
    
    teachers = get_teachers()
    if request.method == 'POST':
        test.title = request.form.get('title').strip()
        test.teacher_id = int(request.form.get('teacher_id'))
        db.session.commit()
        flash('Test updated successfully.', 'success')
        return redirect(url_for('tests'))

    return render_template('test_form.html', mode='edit', test=test, teachers=teachers)


@app.route('/tests/<int:test_id>/delete', methods=['POST'])
def delete_test(test_id):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM answers WHERE test_id = :test_id"), {"test_id": test_id})
        conn.execute(text("DELETE FROM grades WHERE test_id = :test_id"), {"test_id": test_id})
        conn.execute(text("DELETE FROM questions WHERE test_id = :test_id"), {"test_id": test_id})
        conn.execute(text("DELETE FROM tests WHERE test_id = :test_id"), {"test_id": test_id})
        conn.commit()

    flash('Test deleted.', 'success')
    return redirect(url_for('tests'))


@app.route('/tests/<int:test_id>/editor', methods=['GET', 'POST'])
def test_editor(test_id):
    test = get_test_obj(test_id)
    if not test:
        flash('Test not found.', 'error')
        return redirect(url_for('tests'))

    test.questions = get_questions_for_test(test_id)

    if request.method == 'POST':
        question_text = request.form.get('text', '').strip()
        if not question_text:
            flash('Question text is required.', 'error')
            return redirect(url_for('test_editor', test_id=test_id))

        with engine.connect() as conn:
            next_q = conn.execute(
                text("""
                    SELECT COALESCE(MAX(q_number), 0) + 1
                    FROM questions
                    WHERE test_id = :test_id
                """),
                {"test_id": test_id}
            ).scalar()

            conn.execute(
                text("""
                    INSERT INTO questions(test_id, q_number, q_txt)
                    VALUES(:test_id, :q_number, :q_txt)
                """),
                {"test_id": test_id, "q_number": next_q, "q_txt": question_text}
            )
            conn.commit()

        return redirect(url_for('test_editor', test_id=test_id))

    return render_template('test_editor.html', test=test)


@app.route('/tests/<int:test_id>/questions/<int:q_number>/delete', methods=['POST'])
def delete_question(test_id, q_number):
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM answers WHERE test_id = :test_id AND q_number = :q_number"),
            {"test_id": test_id, "q_number": q_number}
        )
        conn.execute(
            text("DELETE FROM questions WHERE test_id = :test_id AND q_number = :q_number"),
            {"test_id": test_id, "q_number": q_number}
        )
        conn.commit()

    flash('Question deleted.', 'success')
    return redirect(url_for('test_editor', test_id=test_id))


@app.route('/tests/<int:test_id>/questions/<int:question_id>/edit', methods=['GET', 'POST'])
def edit_question(test_id, question_id):
    question = get_question(question_id)
    if not question:
        flash('Question not found.', 'error')
        return redirect(url_for('test_editor', test_id=test_id))
    
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        if not text:
            flash('Question text is required.', 'error')
            return redirect(url_for('test_editor', test_id=test_id))
        
        # CHANGE: Update the existing question object instead of creating a new one
        question.text = text
        db.session.commit()
        
        flash('Question updated.', 'success')
        return redirect(url_for('test_editor', test_id=test_id))

    return render_template('edit_question.html', test_id=test_id, question=question)


@app.route('/take-test', methods=['GET', 'POST'])
def take_test_select():
    students = get_students()
    if not students:
        students = [get_user(u['acct_id']) for u in get_all_users() if not u['isTeacher']]
    tests_list = get_all_tests()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        test_id = request.form.get('test_id')
        if not student_id or not test_id:
            flash('Select both student and test.', 'error')
            return redirect(url_for('take_test_select'))
        return redirect(url_for('take_test', test_id=int(test_id), student_id=int(student_id)))

    return render_template('take_test_select.html', students=students, tests=tests_list)


@app.route('/take-test/<int:test_id>/<int:student_id>', methods=['GET', 'POST'])
def take_test(test_id, student_id):
    student = get_person(student_id)
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('take_test_select'))
    
    test_obj = get_test_obj(test_id)
    if not test_obj:
        flash('Test not found.', 'error')
        return redirect(url_for('take_test_select'))
    
    questions = Question.query.filter_by(test_id=test_id).all()

    if request.method == 'POST':
        if not questions:
            flash('No questions to take.', 'error')
            return redirect(url_for('take_test_select'))

        response = Response(student_id=student.id, test_id=test_obj.id)
        db.session.add(response)
        db.session.commit()

        for question in questions:
            submitted_text = request.form.get(f'q_{question.id}', '').strip()
            answer = Answer(response_id=response.id, question_id=question.id, content=submitted_text)
            db.session.add(answer)

        db.session.commit()

        flash('Test submitted. Your grade: ' + str(calculate_grade(response)), 'success')
        return redirect(url_for('responses', test_id=test_id))

    return render_template('take_test.html', student=student, test=test_obj, questions=questions)


@app.route('/responses')
def responses():
    test_id = request.args.get('test_id', type=int)
    tests_list = get_all_tests()
    selected_test = None
    response_items = []
    if test_id:
        selected_test = get_test_obj(test_id)
        if selected_test:
            db_responses = Response.query.filter_by(test_id=test_id).order_by(Response.submitted_at.desc()).all()
            if db_responses:
                response_items = [{'response': r, 'grade': calculate_grade(r)} for r in db_responses]
            else:
                response_items = [{'response': r, 'grade': get_grade_for(test_id, r.student_id) or 0} for r in get_responses_for_test(test_id)]
    return render_template('responses.html', tests=tests_list, selected_test=selected_test, response_items=response_items)


@app.route('/responses/test/<int:test_id>/student/<int:student_id>')
def response_detail(test_id, student_id):
    selected_test = get_test_obj(test_id)
    student = get_person(student_id)
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('responses', test_id=test_id))

    response = Response.query.filter_by(test_id=test_id, student_id=student_id).order_by(Response.submitted_at.desc()).first()
    if response:
        answers = response.answers
        grade = calculate_grade(response)
        return render_template('response_detail.html', test=selected_test, student=student, response=response, answers=answers, grade=grade)

    answers = get_answers_for(test_id, student_id)
    if not answers:
        flash('No response found for this student/test.', 'error')
        return redirect(url_for('responses', test_id=test_id))

    fake_answer_objects = []
    for a in answers:
        question = next((q for q in get_questions_for_test(test_id) if q.q_number == a['q_number']), None)
        if question is not None:
            
            fake_answer_objects.append(SimpleNamespace(question=question, content=a['answer']))

    grade = get_grade_for(test_id, student_id) or 0
    fake_response = SimpleNamespace(test_id=test_id, student_id=student_id, submitted_at=datetime.now(), answers=fake_answer_objects)
    return render_template('response_detail.html', test=selected_test, student=student, response=fake_response, answers=fake_answer_objects, grade=grade)


@app.route('/students')
def students():
    students = get_students()
    return render_template('students.html', students=students)


@app.route('/students/<int:student_id>')
def student_detail(student_id):
    student = get_person(student_id)
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('students'))
    responses_list = Response.query.filter_by(student_id=student_id).all()
    summary = []
    for r in responses_list:
        summary.append({'test': r.test, 'grade': calculate_grade(r), 'submitted_at': r.submitted_at})
    return render_template('student_detail.html', student=student, summary=summary)

@app.route('/update_grade/<int:response_id>', methods=['POST'])
def update_grade(response_id):
    response = Response.query.get_or_404(response_id)
    new_grade = request.form.get('grade')
    if new_grade:
        response.grade = new_grade
        db.session.commit()
        flash('Grade updated!', 'success')
    return redirect(url_for('responses', test_id=response.test_id))

if __name__ == '__main__':
    app.run(debug=True)
