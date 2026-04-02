from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, create_engine, Connection, text
from sqlalchemy.orm import sessionmaker
import hashlib as hash
import random

def db_exists(user:str, password:str, server:str, db_name:str) -> bool:
    """
    Check if the Database exists on the server
    """
    connection_str = f"mysql://{user}:{password}@{server}"
    engine = create_engine(connection_str, echo=True, connect_args={"local_infile":1})
    with engine.connect() as conn:
        result = conn.execute(text("SHOW DATABASES"))
        databases = [row[0] for row in result.fetchall()]
    engine.dispose()
    return db_name in databases

def create_db(user:str, password:str, server:str, db_name:str):
    """runs the query to create an empty database"""
    connection_str = f"mysql://{user}:{password}@{server}/{db_name}"
    engine = create_engine(connection_str, echo=True, connect_args={"local_infile":1})
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {db_name}"))
        _create_tables(conn)
    engine.dispose()

def _create_tables(conn:Connection):
    queries = [
        """CREATE TABLE accounts(
            acct_id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(32) NOT NULL,
            is_teacher BOOLEAN DEFAULT FALSE
        )""",
        """CREATE TABLE tests(
            test_id INT PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(128) NOT NULL,
            teacher_id INT,
            CONSTRAINT fk_tests_teacher_id FOREIGN KEY (teacher_id) REFERENCES accounts(acct_id)
        )""",
        """CREATE TABLE grades(
            test_id INT,
            student_id INT,
            grade INT,
            PRIMARY KEY(test_id, student_id),
            CONSTRAINT fk_grades_test_id FOREIGN KEY (test_id) REFERENCES tests(test_id),
            CONSTRAINT fk_grades_student_id FOREIGN KEY (student_id) REFERENCES accounts(acct_id),
            CONSTRAINT range_grades CHECK (grade >= 0 AND grade <= 100)
        )""",
        """CREATE TABLE questions(
            test_id INT,
            q_number INT,
            q_txt VARCHAR(512),
            PRIMARY KEY(test_id, q_number),
            CONSTRAINT fk_questions_test_id FOREIGN KEY (test_id) REFERENCES tests(test_id)
        )""",
        """CREATE TABLE answers(
            test_id INT,
            q_number INT,
            student_id INT,
            answer VARCHAR(4080),
            PRIMARY KEY(test_id, student_id, q_number),
            CONSTRAINT fk_answers_test_question FOREIGN KEY (test_id, q_number) REFERENCES questions(test_id, q_number)
        )""",
    ]
    for query in queries:
        conn.execute(text(query))
    
    students = ["Sparkles Junior",
                "Richard Little",
                "Bart Smimpson",
                "Joe Schmoe",
                "Peter Short"]
    teachers = ["Mr C",
                "Mr Arjona",
                "Mr Ackerman",
                "Dr Bogale",
                "Mr M"]
    
    for name in students:
        query = f"""INSERT INTO accounts(name, is_teacher)
                    VALUES("{name}", FALSE)"""
        conn.execute(text(query))
        
    for name in teachers:
        query = f"""INSERT INTO accounts(name, is_teacher)
                    VALUES("{name}", TRUE)"""
        conn.execute(text(query))

    query = """INSERT INTO tests(title, teacher_id)
                VALUES("The quest for the holy grail", 8)"""
    conn.execute(text(query))

    questions = ["What is your name?",
                 "What is your favorite color?",
                 "What is the capital of Assyria?",
                 "What is the airspeed velocity of an unladen swallow?"]
    
    for i, question in enumerate(questions):
        query = f"""INSERT INTO questions(test_id, q_number, q_txt)
                    Values(1,{i+1}, "{question}")"""
        conn.execute(text(query))
    
    conn.commit()