from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from types import SimpleNamespace

app = Flask(__name__)
app.config['SECRET_KEY'] = 'devkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    tests = db.relationship('Test', backref='teacher', lazy=True)
    responses = db.relationship('Response', backref='student', lazy=True)


class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    questions = db.relationship('Question', backref='test', lazy=True, cascade='all, delete-orphan')
    responses = db.relationship('Response', backref='test', lazy=True, cascade='all, delete-orphan')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')


class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.now)
    grade = db.Column(db.String(20), default="Ungraded")
    answers = db.relationship('Answer', backref='response', lazy=True, cascade='all, delete-orphan')

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    content = db.Column(db.Text, nullable=False) 


# mock dictionaries (Table translation reference)
MOCK_ACCOUNTS = [
    {'acct_id': 1, 'name': 'Ms. Carter', 'isTeacher': True, 'email': 'carter@school.edu'},
    {'acct_id': 2, 'name': 'Mr. Lee', 'isTeacher': True, 'email': 'lee@school.edu'},
    {'acct_id': 3, 'name': 'Ava Williams', 'isTeacher': False, 'email': 'ava@school.edu'},
    {'acct_id': 4, 'name': 'Noah Singh', 'isTeacher': False, 'email': 'noah@school.edu'},
]

MOCK_TESTS = [
    {'test_id': 1, 'title': 'Biology 101', 'teacher_id': 1},
    {'test_id': 2, 'title': 'World History', 'teacher_id': 2},
]

MOCK_QUESTIONS = [
    {'test_id': 1, 'q_number': 1, 'q_txt': 'What is the powerhouse of the cell?'},
    {'test_id': 1, 'q_number': 2, 'q_txt': 'DNA stands for?'},
    {'test_id': 2, 'q_number': 1, 'q_txt': 'Who founded Rome according to myth?'},
]

MOCK_GRADES = [
    {'test_id': 1, 'student_id': 3, 'grade': 92},
    {'test_id': 1, 'student_id': 4, 'grade': 81},
    {'test_id': 2, 'student_id': 3, 'grade': 88},
]

MOCK_ANSWERS = [
    {'test_id': 1, 'q_number': 1, 'student_id': 3, 'answer': 'Mitochondria'},
    {'test_id': 1, 'q_number': 2, 'student_id': 3, 'answer': 'Deoxyribonucleic acid'},
]

with app.app_context():
    db.create_all()

    if not User.query.first():
        for acc in MOCK_ACCOUNTS:
            role = 'teacher' if acc['isTeacher'] else 'student'
            u = User(id=acc['acct_id'], name=acc['name'], email=acc['email'], role=role)
            db.session.add(u)

    if not Test.query.first():
        for t in MOCK_TESTS:
            db.session.add(Test(id=t['test_id'], title=t['title'], teacher_id=t['teacher_id']))

    if not Question.query.first():
        for q in MOCK_QUESTIONS:
            db.session.add(Question(test_id=q['test_id'], text=q['q_txt']))

    if not Response.query.first():
        for g in MOCK_GRADES:
            student = User.query.filter_by(id=g['student_id']).first()
            if student:
                response = Response(test_id=g['test_id'], student_id=g['student_id'])
                db.session.add(response)
                db.session.flush()
                for ans in [x for x in MOCK_ANSWERS if x['test_id'] == g['test_id'] and x['student_id'] == g['student_id']]:
                    question = Question.query.filter_by(test_id=ans['test_id']).order_by(Question.id).offset(ans['q_number']-1).first()
                    if question:
                        db.session.add(Answer(response_id=response.id, question_id=question.id, content=ans['answer']))

    db.session.commit()



def get_mock_user(acct_id):
    row = next((x for x in MOCK_ACCOUNTS if x['acct_id'] == acct_id), None)
    if not row:
        return None
    return SimpleNamespace(id=row['acct_id'], name=row['name'], email=row.get('email', ''), role='teacher' if row['isTeacher'] else 'student')


def get_all_users():
    users = User.query.all()
    if users:
        return users
    return [get_mock_user(r['acct_id']) for r in MOCK_ACCOUNTS]


def get_all_tests():
    tests = Test.query.all()
    if tests:
        return tests
    return [SimpleNamespace(id=x['test_id'], title=x['title'], teacher=get_mock_user(x['teacher_id']), questions=get_mock_questions(x['test_id']), responses=get_mock_responses_for_test(x['test_id'])) for x in MOCK_TESTS]


def get_test_obj(test_id):
    t = Test.query.get(test_id)
    if t:
        return t
    row = next((x for x in MOCK_TESTS if x['test_id'] == test_id), None)
    if not row:
        return None
    return SimpleNamespace(id=row['test_id'], title=row['title'], teacher=get_mock_user(row['teacher_id']), questions=get_mock_questions(test_id), responses=get_mock_responses_for_test(test_id))


def get_mock_questions(test_id):
    db_questions = Question.query.filter_by(test_id=test_id).all()
    if db_questions:
        return db_questions
    return [SimpleNamespace(id=(test_id * 100 + q['q_number']), 
        test_id=test_id, 
        q_number=q['q_number'], 
        text=q['q_txt']) for q in MOCK_QUESTIONS if q['test_id'] == test_id]

def get_mock_responses_for_test(test_id):
    responses = Response.query.filter_by(test_id=test_id).all()
    if responses:
        return responses
    # fallback simple mock with grade tracking from MOCK_GRADES
    rows = []
    for g in [x for x in MOCK_GRADES if x['test_id'] == test_id]:
        student = get_mock_user(g['student_id'])
        rows.append(SimpleNamespace(id=999 + g['student_id'], test_id=test_id, student_id=g['student_id'], student=student, submitted_at=datetime.now(), answers=[]))
    return rows


def get_grade_for(test_id, student_id):
    g = next((x for x in MOCK_GRADES if x['test_id'] == test_id and x['student_id'] == student_id), None)
    if g:
        return g['grade']
    return None


def get_answers_for(test_id, student_id):
    filtered = [x for x in MOCK_ANSWERS if x['test_id'] == test_id and x['student_id'] == student_id]
    return filtered


def calculate_grade(response):
    return response.grade if hasattr(response, 'grade') else "Ungraded"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        email = request.form.get('email').strip()
        role = request.form.get('role')

        if not name or not email or not role:
            flash('Name, email, and role are required.', 'error')
            return redirect(url_for('register'))

        user = User(name=name, email=email, role=role)
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
        role='all'
        
    return render_template('accounts.html', users=users, selected_role=role)


@app.route('/tests')
def tests():
    tests = Test.query.order_by(Test.created_at.desc()).all()
    if not tests:
        tests = get_all_tests()
    return render_template('tests.html', tests=tests)


@app.route('/tests/create', methods=['GET', 'POST'])
def create_test():
    teachers = User.query.filter_by(role='teacher').all()
    if request.method == 'POST':
        title = request.form.get('title').strip()
        teacher_id = request.form.get('teacher_id')
        if not title or not teacher_id:
            flash('Test title and teacher are required.', 'error')
            return redirect(url_for('create_test'))

        test = Test(title=title, teacher_id=int(teacher_id))
        db.session.add(test)
        db.session.commit()
        flash('Test created successfully.', 'success')
        return redirect(url_for('tests'))

    return render_template('test_form.html', mode='create', teachers=teachers)


@app.route('/tests/<int:test_id>/edit', methods=['GET', 'POST'])
def edit_test(test_id):
    test = Test.query.get_or_404(test_id)
    teachers = User.query.filter_by(role='teacher').all()
    if request.method == 'POST':
        test.title = request.form.get('title').strip()
        test.teacher_id = int(request.form.get('teacher_id'))
        db.session.commit()
        flash('Test updated successfully.', 'success')
        return redirect(url_for('tests'))

    return render_template('test_form.html', mode='edit', test=test, teachers=teachers)


@app.route('/tests/<int:test_id>/delete', methods=['POST'])
def delete_test(test_id):
    test = Test.query.get_or_404(test_id)
    db.session.delete(test)
    db.session.commit()
    flash('Test deleted.', 'success')
    return redirect(url_for('tests'))


@app.route('/tests/<int:test_id>/editor', methods=['GET', 'POST'])
def test_editor(test_id):
    test = get_test_obj(test_id)
    if not test:
        flash('Test not found.', 'error')
        return redirect(url_for('tests'))
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        if not text:
            flash('Question text is required.', 'error')
            return redirect(url_for('test_editor', test_id=test_id))
        q = Question(test_id=test_id, text=text) 
        db.session.add(q)
        db.session.commit()
        return redirect(url_for('test_editor', test_id=test_id))

    return render_template('test_editor.html', test=test)


@app.route('/tests/<int:test_id>/questions/<int:question_id>/delete', methods=['POST'])
def delete_question(test_id, question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted.', 'success')
    return redirect(url_for('test_editor', test_id=test_id))


@app.route('/tests/<int:test_id>/questions/<int:question_id>/edit', methods=['GET', 'POST'])
def edit_question(test_id, question_id):
    question = Question.query.get_or_404(question_id)
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
    students = User.query.filter_by(role='student').all()
    if not students:
        students = [get_mock_user(u['acct_id']) for u in MOCK_ACCOUNTS if not u['isTeacher']]
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
    student = User.query.filter_by(id=student_id, role='student').first_or_404()
    test_obj = Test.query.get_or_404(test_id)
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
                response_items = [{'response': r, 'grade': get_grade_for(test_id, r.student_id) or 0} for r in get_mock_responses_for_test(test_id)]
    return render_template('responses.html', tests=tests_list, selected_test=selected_test, response_items=response_items)


@app.route('/responses/test/<int:test_id>/student/<int:student_id>')
def response_detail(test_id, student_id):
    selected_test = Test.query.get_or_404(test_id)
    student = User.query.filter_by(id=student_id, role='student').first_or_404()
    response = Response.query.filter_by(test_id=test_id, student_id=student_id).order_by(Response.submitted_at.desc()).first()
    if response:
        answers = response.answers
        grade = calculate_grade(response)
        return render_template('response_detail.html', test=selected_test, student=student, response=response, answers=answers, grade=grade)

    mock_answers = get_answers_for(test_id, student_id)
    if not mock_answers:
        flash('No response found for this student/test.', 'error')
        return redirect(url_for('responses', test_id=test_id))

    fake_answer_objects = []
    for a in mock_answers:
        question = next((q for q in get_mock_questions(test_id) if q.q_number == a['q_number']), None)
        if question is not None:
            
            fake_answer_objects.append(SimpleNamespace(question=question, content=a['answer']))

    grade = get_grade_for(test_id, student_id) or 0
    fake_response = SimpleNamespace(test_id=test_id, student_id=student_id, submitted_at=datetime.now(), answers=fake_answer_objects)
    return render_template('response_detail.html', test=selected_test, student=student, response=fake_response, answers=fake_answer_objects, grade=grade)


@app.route('/students')
def students():
    students = User.query.filter_by(role='student').all()
    return render_template('students.html', students=students)


@app.route('/students/<int:student_id>')
def student_detail(student_id):
    student = User.query.filter_by(id=student_id, role='student').first_or_404()
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
