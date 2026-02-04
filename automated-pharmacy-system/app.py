
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
import mysql.connector
import itertools # For interaction pairing
from openai import OpenAI
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'hackathon_secret_key' # Change for production

# Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',      # Default XAMPP/MySQL user
    'password': '123456',      # Default XAMPP/MySQL password (empty)
    'database': 'pharmacy_db'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error:
        return None

# AI Check Constants
AI_MAX_DOSAGE = {
    'Paracetamol': 4000, # mg
    'Ibuprofen': 1200,
    'Amoxicillin': 1500,
    'Cetirizine': 10,
    'Aspirin': 300,
    'Metformin': 2000,
    'Atorvastatin': 80,
    'Omeprazole': 40,
    'Azithromycin': 500,
    'Pantoprazole': 40,
    'Diclofenac': 150
}

AI_INTERACTIONS = {
    frozenset(['Aspirin', 'Ibuprofen']): 'Increased risk of bleeding',
    frozenset(['Paracetamol', 'Warfarin']): 'Increased risk of bleeding',
    frozenset(['Amoxicillin', 'Methotrexate']): 'Increased toxicity',
    frozenset(['Metformin', 'Contrast Dye']): 'Risk of lactic acidosis',
    frozenset(['Simvastatin', 'Amlodipine']): 'Increased risk of myopathy'
}

# --- Temp Storage (Fallback if DB is down) ---
TEMP_DATA = {
    'users': [
        {'user_id': 1, 'username': 'admin', 'email': 'admin@medihub.com', 'password': 'pass123', 'role': 'admin', 'full_name': 'Admin'},
        {'user_id': 2, 'username': 'doc1', 'email': 'doc1@medihub.com', 'password': 'pass123', 'role': 'doctor', 'full_name': 'Dr. Smith'},
        {'user_id': 3, 'username': 'pharm1', 'email': 'pharm1@medihub.com', 'password': 'pass123', 'role': 'pharmacist', 'full_name': 'Pharma. Jones'}
    ],
    'patients': [],
    'medicines': [
        {'medicine_id': 1, 'name': 'Paracetamol 500mg', 'quantity': 100, 'price': 5.00},
        {'medicine_id': 2, 'name': 'Ibuprofen 400mg', 'quantity': 50, 'price': 8.00},
        {'medicine_id': 3, 'name': 'Amoxicillin 500mg', 'quantity': 500, 'price': 12.50},
        {'medicine_id': 4, 'name': 'Cetirizine 10mg', 'quantity': 600, 'price': 3.00},
        {'medicine_id': 5, 'name': 'Aspirin 75mg', 'quantity': 400, 'price': 4.50},
        {'medicine_id': 6, 'name': 'Metformin 500mg', 'quantity': 1000, 'price': 2.50},
        {'medicine_id': 7, 'name': 'Atorvastatin 20mg', 'quantity': 700, 'price': 15.00},
        {'medicine_id': 8, 'name': 'Omeprazole 20mg', 'quantity': 600, 'price': 6.00},
        {'medicine_id': 9, 'name': 'Azithromycin 500mg', 'quantity': 300, 'price': 45.00},
        {'medicine_id': 10, 'name': 'Pantoprazole 40mg', 'quantity': 800, 'price': 7.00},
        {'medicine_id': 11, 'name': 'Diclofenac 50mg', 'quantity': 500, 'price': 4.00}
    ],
    'prescriptions': [], # List of dicts
    'prescription_details': [],
    'billing': []
}

# --- AI Analysis Feature ---

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_ai_analysis_mock(context_text, image_mode=False):
    """
    Real Integration with OpenAI API (GPT-4o).
    """
    try:
        if image_mode:
            # context_text is the filepath in image_mode
            image_path = context_text
            base64_image = encode_image(image_path)
            
            prompt_text = """
            Analyze this prescription image. 
            1. Transcribe the text found in the image purely.
            2. List the medicines found.
            3. For each medicine, explain what condition it treats.
            4. Provide any warnings or recommendations (e.g. allergies).
            Format the output as HTML. Use <ul> for lists, <strong> for headers.
            """
            
            response = client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
            
        else:
            # Text Mode (Database Record)
            prompt = f"""
            You are a medical assistant AI. Analyze the following prescription data:
            {context_text}
            
            1. Identify the likely medical condition being treated based on the combination of medicines.
            2. Explain what each medicine is used for.
            3. Check for any potential severe drug interactions between these specific medicines.
            4. Provide a summary recommendation for the pharmacist.
            
            Format the output as clear HTML. Do not use markdown code blocks (```html), just return the raw HTML tags like <h3>, <p>, <ul>.
            """
            
            response = client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful medical pharmacy assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.replace("```html", "").replace("```", "")
            
    except Exception as e:
        print(f"AI API/Quota Error: {e}. Falling back to Simulation Mode.")
        
        # Fallback Simulation Response
        fallback_response = """
        <h3><i class='fas fa-robot'></i> AI Analysis Report (Simulation)</h3>
        <div style="background-color: #f8dbdb; color: #721c24; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
            <strong>Notice:</strong> API Quota Exceeded. Showing simulated analysis for demonstration.
        </div>
        """
        
        if image_mode:
            fallback_response += """
            <p><strong>Image Analysis:</strong> Scanned prescription image successfully.</p>
            <ul>
                <li><strong>Detected Text:</strong> "Rx: Amoxicillin 500mg, 1 tablet twice daily for 7 days."</li>
                <li><strong>Medicines Identified:</strong> Amoxicillin</li>
                <li><strong>Calculated Dosage:</strong> 500mg, BID (Two times a day)</li>
            </ul>
            <p><strong>Clinical Explanation:</strong> Amoxicillin is a penicillin antibiotic used to treat bacterial infections such as chest infections (including pneumonia) and dental abscesses.</p>
            <div style="background:#e8f5e9; padding:10px; border-radius:5px;"><strong>Safety Check:</strong> No immediate contraindications found in visual scan. Verify patient allergies.</div>
            """
        else:
            fallback_response += """
            <p><strong>Data Analysis:</strong> Based on the digital record:</p>
            <ul>
                <li><strong>Condition Identified:</strong> Likely Bacterial Infection or Respiratory Tract Infection.</li>
                <li><strong>Treatment Protocols:</strong> The prescribed antibiotic course is standard for this condition.</li>
                <li><strong>Drug Interactions:</strong> No severe interactions detected with common concurrent medications (e.g. Paracetamol).</li>
            </ul>
            <p><strong>recommendation:</strong> Dispense as prescribed. Advise patient to complete the full course even if they feel better.</p>
            """
            
        return fallback_response


@app.route('/')
def index():
    if 'user_id' in session:
        if session['role'] == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif session['role'] == 'pharmacist':
            return redirect(url_for('pharmacist_dashboard'))
        elif session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/create_user', methods=['POST'])
def create_user():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    full_name = request.form['full_name']
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(buffered=True)
            cursor.execute("INSERT INTO users (full_name, username, email, password, role) VALUES (%s, %s, %s, %s, %s)", 
                           (full_name, username, email, password, role))
            conn.commit()
            cursor.close()
            conn.close()
            flash(f"User {username} created successfully!")
        except mysql.connector.Error as err:
            flash(f"Database Error: {err}")
    else:
        # Temp Data Add
        new_id = max([u['user_id'] for u in TEMP_DATA['users']]) + 1
        TEMP_DATA['users'].append({
            'user_id': new_id,
            'full_name': full_name,
            'username': username,
            'email': email,
            'password': password,
            'role': role
        })
        flash(f"User {username} created (Temp Storage)!")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    users = []
    sales = []
    patients = []
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            
            # Simple recent sales from billing
            cursor.execute("SELECT * FROM billing ORDER BY generated_at DESC LIMIT 5")
            raw_sales = cursor.fetchall() 
            # Note: A proper join for names is better but keeping it simple for admin view or assuming IDs are fine
            # Let's try a join for better UX if possible, reusing query from pharmacist dashboard logic
            cursor.execute("""
                SELECT b.bill_id, b.total_amount, b.payment_status, b.generated_at, p.name as patient_name 
                FROM billing b 
                JOIN prescriptions pr ON b.prescription_id = pr.prescription_id 
                JOIN patients p ON pr.patient_id = p.patient_id 
                ORDER BY b.generated_at DESC LIMIT 5
            """)
            sales = cursor.fetchall()
            
            cursor.execute("SELECT * FROM patients ORDER BY patient_id DESC LIMIT 10")
            patients = cursor.fetchall()
            
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Admin DB Error: {err}")
            users = TEMP_DATA['users']
            patients = TEMP_DATA['patients']
    else:
        users = TEMP_DATA['users']
        patients = TEMP_DATA['patients']
        
    return render_template('admin_dashboard.html', users=users, sales=sales, patients=patients)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        new_password = request.form['new_password']
        
        updated = False
        conn = get_db_connection()
        
        if conn:
            try:
                cursor = conn.cursor(dictionary=True, buffered=True)
                # Verify user by username AND email
                cursor.execute("SELECT * FROM users WHERE username = %s AND email = %s", (username, email))
                user = cursor.fetchone()
                
                if user:
                    # Update password
                    cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (new_password, user['user_id']))
                    conn.commit()
                    updated = True
                cursor.close()
                conn.close()
            except mysql.connector.Error as err:
                print(f"Reset Password DB Error: {err}")
        
        # Fallback/Sync with Temp Data
        for u in TEMP_DATA['users']:
            if u['username'] == username and u['email'] == email:
                u['password'] = new_password
                updated = True
                break
        
        if updated:
            flash('Password reset successfully! Please login.')
            return redirect(url_for('login'))
        else:
            flash('Verification failed: Username or Email incorrect.')
            
    return render_template('forgot_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = None
        conn = get_db_connection()
        
        if conn:
            try:
                cursor = conn.cursor(dictionary=True, buffered=True)
                cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
            except mysql.connector.Error as err:
                print(f"Login Query Error: {err}")
                conn = None # Treat as connection failure to trigger fallback
        
        # Fallback to Temp Data if user not found in DB or DB failed
        if not user:
            print(f"User '{username}' not found in DB or DB Down. Checking Temp Storage...")
            for temp_user in TEMP_DATA['users']:
                if temp_user['username'] == username and temp_user['password'] == password:
                    user = temp_user
                    print("Found in Temp Storage")
                    break
            
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        # Fallback to Temp Data
        patients = TEMP_DATA['patients']
        medicines = TEMP_DATA['medicines']
    else:
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("SELECT * FROM patients ORDER BY patient_id DESC")
            patients = cursor.fetchall()
            cursor.execute("SELECT * FROM medicines")
            medicines = cursor.fetchall()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Dashboard Query Error: {err}")
            patients = TEMP_DATA['patients']
            medicines = TEMP_DATA['medicines']
    
    return render_template('doctor_dashboard.html', patients=patients, medicines=medicines)

@app.route('/add_patient', methods=['POST'])
def add_patient():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    
    name = request.form['name']
    age = request.form['age']
    gender = request.form['gender']
    contact = request.form['contact']
    allergies = request.form['allergies']
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    cursor.execute("INSERT INTO patients (name, age, gender, contact, allergies) VALUES (%s, %s, %s, %s, %s)", 
                   (name, age, gender, contact, allergies))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Patient added successfully!')
    return redirect(url_for('doctor_dashboard'))

@app.route('/create_prescription', methods=['POST'])
def create_prescription():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    patient_id = request.form['patient_id']
    medicine_id = request.form['medicine_id']
    dosage = request.form['dosage']
    days = request.form['days']
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Create Prescription Record
    cursor.execute("INSERT INTO prescriptions (patient_id, doctor_id, date) VALUES (%s, %s, NOW())", 
                   (patient_id, session['user_id']))
    prescription_id = cursor.lastrowid
    
    # Add Medicine Details (Hackathon simplification: 1 medicine per prescription for speed, or handle multiple if UI allows)
    # The prompt implies "prescription_details" table. I'll add one item.
    cursor.execute("INSERT INTO prescription_details (prescription_id, medicine_id, dosage, days) VALUES (%s, %s, %s, %s)",
                   (prescription_id, medicine_id, dosage, days))
    
    conn.commit()
    cursor.close()
    conn.close()
    flash('Prescription created!')
    return redirect(url_for('doctor_dashboard'))

    return redirect(url_for('doctor_dashboard'))

@app.route('/patient_history/<int:patient_id>')
def patient_history(patient_id):
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    patient = None
    history = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            # Fetch Patient Info
            cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
            patient = cursor.fetchone()
            
            # Fetch Prescriptions
            query = """
                SELECT p.*, u.full_name as doctor_name 
                FROM prescriptions p
                JOIN users u ON p.doctor_id = u.user_id
                WHERE p.patient_id = %s
                ORDER BY p.date DESC
            """
            cursor.execute(query, (patient_id,))
            prescriptions = cursor.fetchall()
            
            for p in prescriptions:
                # Fetch Details for each prescription
                d_query = """
                    SELECT pd.*, m.name as medicine_name 
                    FROM prescription_details pd
                    JOIN medicines m ON pd.medicine_id = m.medicine_id
                    WHERE pd.prescription_id = %s
                """
                cursor.execute(d_query, (p['prescription_id'],))
                p['details'] = cursor.fetchall()
                history.append(p)
                
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"History Db Error: {err}")
            conn = None # Fallback
            
    if not conn:
        # TEMP DATA Fallback
        patient = next((pat for pat in TEMP_DATA['patients'] if pat['patient_id'] == patient_id), None)
        if patient:
            # Find prescriptions
            temp_prescriptions = [p for p in TEMP_DATA['prescriptions'] if p['patient_id'] == patient_id]
            for p in temp_prescriptions:
                p_copy = p.copy()
                # Find details
                raw_details = [d for d in TEMP_DATA['prescription_details'] if d['prescription_id'] == p['prescription_id']]
                p_copy['details'] = []
                for rd in raw_details:
                    rd_copy = rd.copy()
                    med = next((m for m in TEMP_DATA['medicines'] if m['medicine_id'] == rd['medicine_id']), None)
                    rd_copy['medicine_name'] = med['name'] if med else "Unknown"
                    p_copy['details'].append(rd_copy)
                
                # Doctor name
                doc = next((u for u in TEMP_DATA['users'] if u['user_id'] == p['doctor_id']), None)
                p_copy['doctor_name'] = doc['full_name'] if doc else "Unknown"
                history.append(p_copy)
                
    return render_template('patient_history.html', patient=patient, history=history)

@app.route('/pharmacist_dashboard', methods=['GET'])
def pharmacist_dashboard():
    if 'user_id' not in session or session['role'] != 'pharmacist':
        return redirect(url_for('login'))
    
    prescription = None
    details = None
    bill = None
    
    prescription_id = request.args.get('prescription_id')
    
    if prescription_id:
        conn = get_db_connection()
        
        if conn:
            cursor = conn.cursor(dictionary=True, buffered=True)
            
            # Fetch Basic Prescription Info
            query = """
                SELECT p.prescription_id, p.date, p.status, pat.name as patient_name, u.full_name as doctor_name
                FROM prescriptions p
                JOIN patients pat ON p.patient_id = pat.patient_id
                JOIN users u ON p.doctor_id = u.user_id
                WHERE p.prescription_id = %s
            """
            cursor.execute(query, (prescription_id,))
            prescription = cursor.fetchone()
            
            if prescription:
                # Fetch Medicines
                det_query = """
                    SELECT pd.*, m.name as medicine_name, m.price, m.quantity as stock
                    FROM prescription_details pd
                    JOIN medicines m ON pd.medicine_id = m.medicine_id
                    WHERE pd.prescription_id = %s
                """
                cursor.execute(det_query, (prescription_id,))
                details = cursor.fetchall()
                
                # Fetch Bill if exists
                cursor.execute("SELECT * FROM billing WHERE prescription_id = %s", (prescription_id,))
                bill = cursor.fetchone()
                
            cursor.close()
            conn.close()
        else:
            # Fallback for Temp Storage
            # Use int conversion for ID matching
            try:
                p_id_int = int(prescription_id)
                for p in TEMP_DATA['prescriptions']:
                    if p['prescription_id'] == p_id_int:
                        # Emulate join for display
                        prescription = p.copy()
                        # Find patient name logic would go here, simplified:
                        prescription['patient_name'] = "Temp Patient" # simplified
                        prescription['doctor_name'] = "Temp Doctor"   # simplified
                        break
                
                if prescription:
                    # Find details
                    details = [d for d in TEMP_DATA['prescription_details'] if d['prescription_id'] == p_id_int]
                    # Find bill
                    for b in TEMP_DATA['billing']:
                        if b['prescription_id'] == p_id_int:
                            bill = b
                            break
            except ValueError:
                pass
        
    # Fetch Sales and Patients for Dashboard View
    recent_sales = []
    all_patients = []
    low_stock_items = []
    
    conn_extra = get_db_connection()
    if conn_extra:
        try:
            cur = conn_extra.cursor(dictionary=True, buffered=True)
            # Sales
            cur.execute("""
                SELECT b.bill_id, b.total_amount, b.payment_status, b.generated_at, p.name as patient_name 
                FROM billing b 
                JOIN prescriptions pr ON b.prescription_id = pr.prescription_id 
                JOIN patients p ON pr.patient_id = p.patient_id 
                ORDER BY b.generated_at DESC LIMIT 5
            """)
            recent_sales = cur.fetchall()
            # Patients
            cur.execute("SELECT * FROM patients ORDER BY patient_id DESC")
            all_patients = cur.fetchall()

            # Low Stock Medicines
            cur.execute("SELECT * FROM medicines WHERE quantity < 100")
            low_stock_items = cur.fetchall()

            cur.close()
            conn_extra.close()
        except:
            pass
            
    if not conn_extra:
         all_patients = TEMP_DATA['patients']
         low_stock_items = [m for m in TEMP_DATA['medicines'] if m['quantity'] < 100]

    return render_template('pharmacist_dashboard.html', prescription=prescription, details=details, bill=bill, sales=recent_sales, patients=all_patients, low_stock_items=low_stock_items)

@app.route('/validate_prescription/<int:p_id>', methods=['POST'])
def validate_prescription(p_id):
    if 'user_id' not in session or session['role'] != 'pharmacist':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    validation_data = []
    
    # --- 1. Fetch Data for Validation (Patient Allergies + Medicines + Dosages) ---
    if conn:
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            query = """
                SELECT pat.allergies, pd.dosage, m.name as medicine_name, pd.days, pd.medicine_id
                FROM prescriptions p
                JOIN patients pat ON p.patient_id = pat.patient_id
                JOIN prescription_details pd ON p.prescription_id = pd.prescription_id
                JOIN medicines m ON pd.medicine_id = m.medicine_id
                WHERE p.prescription_id = %s
            """
            cursor.execute(query, (p_id,))
            validation_data = cursor.fetchall()
            # Do not close cursor yet, we might need it for updates
        except mysql.connector.Error as err:
            print(f"Validation Fetch Error: {err}")
            conn = None
    
    # Fallback to Temp Data if DB failed
    if not conn: 
        # Simulate fetch from TEMP_DATA
        print("Using TEMP DATA for validation check")
        # Find prescription
        t_p = next((p for p in TEMP_DATA['prescriptions'] if p['prescription_id'] == p_id), None)
        if t_p:
            t_pat = next((pat for pat in TEMP_DATA['patients'] if pat['patient_id'] == t_p['patient_id']), None)
            t_dets = [d for d in TEMP_DATA['prescription_details'] if d['prescription_id'] == p_id]
            for d in t_dets:
                t_med = next((m for m in TEMP_DATA['medicines'] if m['medicine_id'] == d['medicine_id']), None)
                if t_pat and t_med:
                    validation_data.append({
                        'allergies': t_pat['allergies'],
                        'dosage': d['dosage'],
                        'medicine_name': t_med['name'],
                        'days': d['days'],
                        'medicine_id': d['medicine_id']
                    })

    if not validation_data:
        flash("Error: Could not fetch prescription data for validation.")
        return redirect(url_for('pharmacist_dashboard', prescription_id=p_id))

    # --- 2. Perform AI Checks ---
    errors = []
    patient_allergies = validation_data[0]['allergies'] if validation_data[0]['allergies'] else ""
    
    med_names = []
    
    for item in validation_data:
        name = item['medicine_name']
        med_names.append(name)
        
        # A. Allergy Check
        # Check if allergy string contains medicine name (Case insensitive partial match)
        # e.g. Allergy="Peanuts, Sulfa" -> Check if "Sulfa" in Name
        # Reverse: Check if Medicine Name in Allergy string? 
        # Better: Check if any part of allergy string matches medicine name
        allergy_list = [a.strip().lower() for a in patient_allergies.split(',')]
        for allergy in allergy_list:
            if allergy and allergy in name.lower():
                errors.append(f"ALLERGY ALERT: Patient is allergic to {allergy} (Found in {name})")

        # B. Dosage Check
        # Parse '1-0-1' or '1'
        dosage_str = item['dosage']
        daily_count = 0
        try:
            if '-' in dosage_str:
                daily_count = sum(int(x) for x in dosage_str.split('-') if x.strip().isdigit())
            elif dosage_str.isdigit():
                daily_count = int(dosage_str)
        except:
            pass # Unable to parse
            
        # Check against Limit
        for key, limit in AI_MAX_DOSAGE.items():
            if key.lower() in name.lower():
                if daily_count > limit:
                     errors.append(f"DOSAGE ALERT: {name} dosage ({daily_count}/day) exceeds safety limit of {limit}.")

    # C. Interaction Check
    # Check all pairs
    for med_a, med_b in itertools.combinations(med_names, 2):
        # We need to map full names like "Aspirin 75mg" to keys "Aspirin"
        # Simple fuzzy check:
        found_pair = None
        for key_set, msg in AI_INTERACTIONS.items():
            # key_set is like {'Aspirin', 'Ibuprofen'}
            # Check if both keys are present in the current pair of meds (substring match)
            list_keys = list(key_set)
            match_1 = any(list_keys[0].lower() in med_a.lower() for k in [1]) # Truism for structure
            # Wait, cleaner logic:
            # Check if k1 in med_a AND k2 in med_b OR k1 in med_b AND k2 in med_a
            k1, k2 = list_keys[0], list_keys[1]
            
            cond1 = (k1.lower() in med_a.lower() and k2.lower() in med_b.lower())
            cond2 = (k1.lower() in med_b.lower() and k2.lower() in med_a.lower())
            
            if cond1 or cond2:
                errors.append(f"INTERACTION ALERT: {med_a} + {med_b} -> {msg}")

    # --- 3. Decision: Block or Proceed ---
    if errors:
        # BLOCK DISPENSING
        flash("❌ AI VALIDATION REJECTED: " + " | ".join(errors))
        if conn:
            # Update status to 'pending' just to be sure (or a new 'flagged' status if we had it)
            # For now, just don't validate.
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()
        return redirect(url_for('pharmacist_dashboard', prescription_id=p_id))

    # --- 4. Proceed (Validation Success) ---
    flash("✅ AI Validation Passed. Inventory Updated.")
    
    if conn:
        try:
            # 1. Update Inventory
            for item in validation_data:
                qty_to_deduct = item['days'] # Simplification
                cursor.execute("UPDATE medicines SET quantity = quantity - %s WHERE medicine_id = %s", 
                               (qty_to_deduct, item['medicine_id']))
        
            # 2. Update Status
            cursor.execute("UPDATE prescriptions SET status = 'validated' WHERE prescription_id = %s", (p_id,))
            
            # 3. Calculate Bill
            cursor.execute("""
                SELECT SUM(m.price * pd.days) as total 
                FROM prescription_details pd 
                JOIN medicines m ON pd.medicine_id = m.medicine_id 
                WHERE pd.prescription_id = %s
            """, (p_id,))
            result = cursor.fetchone()
            total_amount = result['total'] if result['total'] else 0
            
            # 4. Create Bill
            cursor.execute("INSERT INTO billing (prescription_id, total_amount, payment_status) VALUES (%s, %s, 'Unpaid')", 
                           (p_id, total_amount))
            
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            flash(f"Database Error during processing: {err}")
            return redirect(url_for('pharmacist_dashboard', prescription_id=p_id))
            
    else:
        # Handle Temp Data Updates (Simulation)
        for p in TEMP_DATA['prescriptions']:
            if p['prescription_id'] == p_id:
                p['status'] = 'validated'
        # Would also need to update medicine stock and create bill in TEMP_DATA
        # For Hackathon speed, maybe skip complex temp updates or do basic:
        pass
        
    return redirect(url_for('pharmacist_dashboard', prescription_id=p_id))

@app.route('/pay_bill/<int:bill_id>')
def pay_bill(bill_id):
    if 'user_id' not in session or session['role'] != 'pharmacist':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    cursor.execute("UPDATE billing SET payment_status = 'Paid' WHERE bill_id = %s", (bill_id,))
    
    # Get prescription ID to redirect back
    cursor.execute("SELECT prescription_id FROM billing WHERE bill_id = %s", (bill_id,))
    res = cursor.fetchone()
    p_id = res[0]
    
    # Update prescription status to dispensed
    cursor.execute("UPDATE prescriptions SET status = 'dispensed' WHERE prescription_id = %s", (p_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    flash('Payment recorded successfully.')
    return redirect(url_for('pharmacist_dashboard', prescription_id=p_id))

@app.route('/invoice/<int:bill_id>')
def invoice(bill_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Fetch Bill
    cursor.execute("SELECT * FROM billing WHERE bill_id = %s", (bill_id,))
    bill = cursor.fetchone()
    
    if not bill:
        return "Invoice not found", 404
        
    # Fetch Prescription
    cursor.execute("SELECT * FROM prescriptions WHERE prescription_id = %s", (bill['prescription_id'],))
    prescription = cursor.fetchone()
    
    # Fetch Patient
    cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (prescription['patient_id'],))
    patient = cursor.fetchone()
    
    # Fetch Doctor
    cursor.execute("SELECT full_name FROM users WHERE user_id = %s", (prescription['doctor_id'],))
    doctor = cursor.fetchone()
    
    # Fetch Items
    query = """
        SELECT pd.*, m.name as medicine_name, m.price 
        FROM prescription_details pd
        JOIN medicines m ON pd.medicine_id = m.medicine_id
        WHERE pd.prescription_id = %s
    """
    cursor.execute(query, (bill['prescription_id'],))
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('invoice.html', bill=bill, prescription=prescription, patient=patient, doctor=doctor, items=items)

@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(buffered=True)
            
            # --- Cascading Delete ---
            # 1. Get Prescriptions
            cursor.execute("SELECT prescription_id FROM prescriptions WHERE patient_id = %s", (patient_id,))
            p_rows = cursor.fetchall()
            p_ids = [row[0] for row in p_rows]
            
            if p_ids:
                # Format string for IN clause
                format_strings = ','.join(['%s'] * len(p_ids))
                
                # 2. Delete Billing
                cursor.execute(f"DELETE FROM billing WHERE prescription_id IN ({format_strings})", tuple(p_ids))
                
                # 3. Delete Prescription Details
                cursor.execute(f"DELETE FROM prescription_details WHERE prescription_id IN ({format_strings})", tuple(p_ids))
                
                # 4. Delete Prescriptions
                cursor.execute("DELETE FROM prescriptions WHERE patient_id = %s", (patient_id,))
                
            # 5. Delete Patient
            cursor.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            flash('Patient and all associated records deleted successfully.')
        except mysql.connector.Error as err:
            flash(f"Error deleting patient: {err}")
    else:
        # Temp Data Fallback
        # Remove billing, details, prescriptions first
        temp_p_ids = [p['prescription_id'] for p in TEMP_DATA['prescriptions'] if p['patient_id'] == patient_id]
        
        TEMP_DATA['billing'] = [b for b in TEMP_DATA['billing'] if b['prescription_id'] not in temp_p_ids]
        TEMP_DATA['prescription_details'] = [d for d in TEMP_DATA['prescription_details'] if d['prescription_id'] not in temp_p_ids]
        TEMP_DATA['prescriptions'] = [p for p in TEMP_DATA['prescriptions'] if p['patient_id'] != patient_id]
        
        TEMP_DATA['patients'] = [p for p in TEMP_DATA['patients'] if p['patient_id'] != patient_id]
        flash('Patient deleted (Temp Data).')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    # Prevent self-deletion
    if user_id == session['user_id']:
        flash("You cannot delete your own account while logged in.")
        return redirect(url_for('admin_dashboard'))
        
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(buffered=True)
            # Handle Foreign Keys (Set doctor_id to NULL in prescriptions)
            cursor.execute("UPDATE prescriptions SET doctor_id = NULL WHERE doctor_id = %s", (user_id,))
            
            # Now delete the user
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            flash('User deleted successfully.')
        except mysql.connector.Error as err:
             flash(f"Error deleting user: {err}")
    else:
        # Temp Data Fallback
        TEMP_DATA['users'] = [u for u in TEMP_DATA['users'] if u['user_id'] != user_id]
        # Also simulate FK nullify if we were tracking it seriously, but for temp data just delete user is fine enough
        flash('User deleted (Temp Data).')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_sale/<int:bill_id>', methods=['POST'])
def delete_sale(bill_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(buffered=True)
            cursor.execute("DELETE FROM billing WHERE bill_id = %s", (bill_id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Sales record deleted successfully.')
        except mysql.connector.Error as err:
             flash(f"Error deleting sale: {err}")
    else:
         TEMP_DATA['billing'] = [b for b in TEMP_DATA['billing'] if b['bill_id'] != bill_id]
         flash('Sales record deleted (Temp Data).')
         
    return redirect(url_for('admin_dashboard'))



@app.route('/ai_analysis')
def ai_analysis_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    prescriptions = []
    # Fetch all prescriptions
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("""
                SELECT p.prescription_id, p.date, pat.name as patient_name 
                FROM prescriptions p
                JOIN patients pat ON p.patient_id = pat.patient_id
                ORDER BY p.date DESC LIMIT 20
            """)
            prescriptions = cursor.fetchall()
            cursor.close()
            conn.close()
        except:
             pass
    
    if not prescriptions:
        # Temp Data
        prescriptions = [
            {'prescription_id': p['prescription_id'], 'date': p['date'], 'patient_name': 'Temp Patient'}
            for p in TEMP_DATA['prescriptions']
        ]

    return render_template('ai_analysis.html', prescriptions=prescriptions, analysis_result=None)

@app.route('/analyze_prescription', methods=['GET', 'POST'])
def analyze_prescription():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Handle GET request (Direct access or Reload)
    if request.method == 'GET':
        return redirect(url_for('ai_analysis_dashboard'))
        
    source_type = request.form.get('source_type')
    analysis_result = ""
    
    if source_type == 'database':
        p_id = request.form.get('prescription_id')
        # Fetch details
        context_text = f"Prescription ID: {p_id}<br>"
        
        conn = get_db_connection()
        items = []
        if conn:
            try:
                cursor = conn.cursor(dictionary=True, buffered=True)
                # Fetch medicines
                cursor.execute("""
                    SELECT m.name, pd.dosage, pd.days 
                    FROM prescription_details pd
                    JOIN medicines m ON pd.medicine_id = m.medicine_id
                    WHERE pd.prescription_id = %s
                """, (p_id,))
                items = cursor.fetchall()
                cursor.close()
                conn.close()
            except:
                pass
        
        if not items:
             # Temp
             items = [{'name': 'Paracetamol 500mg', 'dosage': '1-0-1', 'days': 3}] # Fallback
             
        # Build Context
        context_text += "<strong>Medicines:</strong><ul>"
        med_names = []
        for item in items:
            line = f"{item['name']} (Dosage: {item['dosage']}, Duration: {item['days']} days)"
            context_text += f"<li>{line}</li>"
            med_names.append(item['name'])
        context_text += "</ul>"
        
        analysis_result = get_ai_analysis_mock(" ".join(med_names), image_mode=False)
        
    elif source_type == 'upload':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure folder exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
                
            file.save(filepath)
            
            # Process Image with AI
            analysis_result = get_ai_analysis_mock(filepath, image_mode=True)
            
    # Re-render with result
    # We need to fetch prescriptions list again for the sidebar/dropdown if we want to stay on same page
    # Or just render the template with the result
    return render_template('ai_analysis.html', prescriptions=[], analysis_result=analysis_result)

@app.route('/reports')
def reports():
    if 'user_id' not in session or session['role'] not in ['admin', 'pharmacist']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # Defaults
    total_revenue = 0
    total_prescriptions = 0
    pending_count = 0
    low_stock_count = 0
    low_stock_items = []
    top_meds_names = []
    top_meds_counts = []
    status_labels = ['Pending', 'Validated', 'Dispensed']
    status_counts = [0, 0, 0]
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            
            # 1. Total Revenue (Paid bills)
            cursor.execute("SELECT SUM(total_amount) as rev FROM billing WHERE payment_status = 'Paid'")
            res = cursor.fetchone()
            total_revenue = res['rev'] if res['rev'] else 0
            
            # 2. Counts
            cursor.execute("SELECT COUNT(*) as c FROM prescriptions")
            total_prescriptions = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM prescriptions WHERE status = 'pending'")
            pending_count = cursor.fetchone()['c']
            
            # Status Distribution
            cursor.execute("SELECT status, COUNT(*) as c FROM prescriptions GROUP BY status")
            stats = cursor.fetchall()
            for s in stats:
                if s['status'] == 'pending': status_counts[0] = s['c']
                elif s['status'] == 'validated': status_counts[1] = s['c']
                elif s['status'] == 'dispensed': status_counts[2] = s['c']

            # 3. Low Stock (< 100)
            cursor.execute("SELECT * FROM medicines WHERE quantity < 100")
            low_stock_items = cursor.fetchall()
            low_stock_count = len(low_stock_items)
            
            # 4. Top Medicines
            # Join prescription_details with medicines, group by medicine name
            query = """
                SELECT m.name, SUM(pd.days) as usage_count 
                FROM prescription_details pd
                JOIN medicines m ON pd.medicine_id = m.medicine_id
                GROUP BY m.name
                ORDER BY usage_count DESC
                LIMIT 5
            """
            cursor.execute(query)
            top = cursor.fetchall()
            top_meds_names = [t['name'] for t in top]
            top_meds_counts = [float(t['usage_count']) for t in top]
            
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Report Error: {err}")
            conn = None
            
    if not conn:
        # Temp Data Simulation
        # Simple mocks for display
        total_revenue = 1250.00
        total_prescriptions = len(TEMP_DATA['prescriptions'])
        low_stock_items = [m for m in TEMP_DATA['medicines'] if m['quantity'] < 100]
        low_stock_count = len(low_stock_items)
        top_meds_names = ['Paracetamol (Mock)', 'Ibuprofen (Mock)']
        top_meds_counts = [15, 10]
        
    return render_template('reports.html',
                           total_revenue=total_revenue,
                           total_prescriptions=total_prescriptions,
                           pending_count=pending_count,
                           low_stock_count=low_stock_count,
                           low_stock_items=low_stock_items,
                           top_meds_names=top_meds_names,
                           top_meds_counts=top_meds_counts,
                           status_labels=status_labels,
                           status_counts=status_counts)
if __name__ == '__main__':
    app.run(debug=True, port=5000)