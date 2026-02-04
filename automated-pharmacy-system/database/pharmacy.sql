-- Database Schema for Automated Pharmacy System

DROP DATABASE IF EXISTS pharmacy_db;
CREATE DATABASE pharmacy_db;
USE pharmacy_db;

-- Users Table (Doctors, Pharmacists, Admin)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('doctor', 'pharmacist', 'admin') NOT NULL
);

-- Patients Table
CREATE TABLE patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT,
    gender VARCHAR(10),
    contact VARCHAR(20),
    allergies TEXT
);

-- Medicines Table
CREATE TABLE medicines (
    medicine_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    quantity INT DEFAULT 0,
    price DECIMAL(10, 2) NOT NULL
);

-- Prescriptions Table
CREATE TABLE prescriptions (
    prescription_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT,
    doctor_id INT,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'validated', 'dispensed') DEFAULT 'pending',
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (doctor_id) REFERENCES users(user_id)
);

-- Prescription Details Table (Many-to-Many for Medicines)
CREATE TABLE prescription_details (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    prescription_id INT,
    medicine_id INT,
    dosage VARCHAR(50),
    days INT,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id),
    FOREIGN KEY (medicine_id) REFERENCES medicines(medicine_id)
);

-- Billing Table
CREATE TABLE billing (
    bill_id INT AUTO_INCREMENT PRIMARY KEY,
    prescription_id INT,
    total_amount DECIMAL(10, 2),
    payment_status ENUM('Unpaid', 'Paid') DEFAULT 'Unpaid',
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id)
);

-- Seed Data (Users)
INSERT INTO users (full_name, username, email, password, role) VALUES 
('System Admin', 'admin', 'admin@medihub.com', 'pass123', 'admin'),
('Dr. Smith', 'doc1', 'doctor@medihub.com', 'pass123', 'doctor'),
('Pharma. Jones', 'pharm1', 'pharm@medihub.com', 'pass123', 'pharmacist');

-- Seed Data (Medicines)
INSERT INTO medicines (name, quantity, price) VALUES 
('Paracetamol 500mg', 1000, 5.00),
('Amoxicillin 500mg', 500, 12.50),
('Ibuprofen 400mg', 800, 8.00),
('Cetirizine 10mg', 600, 3.00),
('Aspirin 75mg', 400, 4.50),
('Metformin 500mg', 1000, 2.50),
('Atorvastatin 20mg', 700, 15.00),
('Omeprazole 20mg', 600, 6.00),
('Azithromycin 500mg', 300, 45.00),
('Pantoprazole 40mg', 800, 7.00),
('Diclofenac 50mg', 500, 4.00);


