from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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
    choice_a = db.Column(db.String(255), nullable=False)
    choice_b = db.Column(db.String(255), nullable=False)
    choice_c = db.Column(db.String(255), nullable=False)
    choice_d = db.Column(db.String(255), nullable=False)
    correct_choice = db.Column(db.String(1), nullable=False)
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')


class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.now)
    answers = db.relationship('Answer', backref='response', lazy=True, cascade='all, delete-orphan')


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_choice = db.Column(db.String(1), nullable=False)


with app.app_context():
    db.create_all()


def calculate_grade(response):
    total = len(response.answers)
    if total == 0:
        return 0
    correct = sum(1 for a in response.answers if a.selected_choice == a.question.correct_choice)
    return round((correct / total) * 100, 1)


@app.route('/')
def index():
    return redirect(url_for('tests'))


@app.route('/register/<role>', methods=['GET', 'POST'])
def register(role):
    if role not in ['teacher', 'student']:
        flash('Invalid role', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name').strip()
        email = request.form.get('email').strip()
        if not name or not email:
            flash('Name and email are required.', 'error')
            return redirect(url_for('register', role=role))

        user = User(name=name, email=email, role=role)
        db.session.add(user)
        db.session.commit()
        flash(f'{role.title()} registered successfully.', 'success')
        return redirect(url_for('accounts'))

    return render_template('register.html', role=role)


@app.route('/accounts')
def accounts():
    role = request.args.get('role', 'all')
    if role in ['student', 'teacher']:
        users = User.query.filter_by(role=role).all()
    else:
        users = User.query.all()
    return render_template('accounts.html', users=users, selected_role=role)


@app.route('/tests')
def tests():
    tests = Test.query.order_by(Test.created_at.desc()).all()
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
    test = Test.query.get_or_404(test_id)
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        a = request.form.get('choice_a', '').strip()
        b = request.form.get('choice_b', '').strip()
        c = request.form.get('choice_c', '').strip()
        d = request.form.get('choice_d', '').strip()
        correct = request.form.get('correct_choice')
        if not all([text, a, b, c, d, correct]):
            flash('All fields are required for each question.', 'error')
            return redirect(url_for('test_editor', test_id=test_id))
        q = Question(test_id=test_id, text=text, choice_a=a, choice_b=b, choice_c=c, choice_d=d, correct_choice=correct)
        db.session.add(q)
        db.session.commit()
        flash('Question added.', 'success')
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
        question.text = request.form.get('text', '').strip()
        question.choice_a = request.form.get('choice_a', '').strip()
        question.choice_b = request.form.get('choice_b', '').strip()
        question.choice_c = request.form.get('choice_c', '').strip()
        question.choice_d = request.form.get('choice_d', '').strip()
        question.correct_choice = request.form.get('correct_choice')
        db.session.commit()
        flash('Question updated.', 'success')
        return redirect(url_for('test_editor', test_id=test_id))

    return render_template('edit_question.html', test_id=test_id, question=question)


@app.route('/take-test', methods=['GET', 'POST'])
def take_test_select():
    students = User.query.filter_by(role='student').all()
    tests_list = Test.query.all()
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
            selected = request.form.get(f'q_{question.id}', '')
            if not selected:
                selected = ''
            answer = Answer(response_id=response.id, question_id=question.id, selected_choice=selected)
            db.session.add(answer)

        db.session.commit()

        flash('Test submitted. Your grade: ' + str(calculate_grade(response)) + '%', 'success')
        return redirect(url_for('responses', test_id=test_id))

    return render_template('take_test.html', student=student, test=test_obj, questions=questions)


@app.route('/responses')
def responses():
    test_id = request.args.get('test_id', type=int)
    tests_list = Test.query.all()
    selected_test = None
    response_items = []
    if test_id:
        selected_test = Test.query.get(test_id)
        if selected_test:
            response_items = []
            for r in Response.query.filter_by(test_id=test_id).order_by(Response.submitted_at.desc()).all():
                response_items.append({'response': r, 'grade': calculate_grade(r)})
    return render_template('responses.html', tests=tests_list, selected_test=selected_test, response_items=response_items)


@app.route('/responses/test/<int:test_id>/student/<int:student_id>')
def response_detail(test_id, student_id):
    selected_test = Test.query.get_or_404(test_id)
    student = User.query.filter_by(id=student_id, role='student').first_or_404()
    response = Response.query.filter_by(test_id=test_id, student_id=student_id).order_by(Response.submitted_at.desc()).first()
    if not response:
        flash('No response found for this student/test.', 'error')
        return redirect(url_for('responses', test_id=test_id))

    answers = response.answers
    grade = calculate_grade(response)
    return render_template('response_detail.html', test=selected_test, student=student, response=response, answers=answers, grade=grade)


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


if __name__ == '__main__':
    app.run(debug=True)
