CREATE DATABASE IF NOT EXISTS WeightHelp;

USE WeightHelp;

CREATE TABLE IF NOT EXISTS UserData (username VARCHAR(255) PRIMARY KEY,hashed_password VARCHAR(600));

CREATE TABLE IF NOT EXISTS Courses (username VARCHAR(255), course_code INT PRIMARY KEY,course_name VARCHAR(400));

CREATE TABLE IF NOT EXISTS Components (username VARCHAR(255),course_code INT,component_type VARCHAR(399),Weightage FLOAT,Total_marks FLOAT,Obtained_marks FLOAT);
