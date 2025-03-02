from flask import Blueprint, request, jsonify, current_app, render_template
from backend.services.gemini_service import GeminiService
import os

food_routes = Blueprint('food_routes', __name__)

# Simplified routes without database dependencies
@food_routes.route('/api/food/analyze-text', methods=['POST'])
def analyze_text():
    """Endpoint to analyze food based on text description"""
    data = request.json
    
    if not data or 'text' not in data:
        return jsonify({"error": "No text description provided"}), 400
    
    food_description = data['text']
    
    # Get API key from config
    api_key = current_app.config.get('GEMINI_API_KEY')
    
    # Initialize Gemini service
    try:
        gemini_service = GeminiService(api_key)
        result = gemini_service.analyze_food_text(food_description)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify({"error": result["error"]}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@food_routes.route('/api/food/analyze-image', methods=['POST'])
def analyze_image():
    """Endpoint to analyze food from an uploaded image"""
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400
    
    # Make sure it's an image file
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return jsonify({"error": "File must be an image"}), 400
        
    # Get API key from environment
    api_key = os.environ.get('GEMINI_API_KEY')
    
    # Initialize Gemini service
    try:
        gemini_service = GeminiService(api_key)
        result = gemini_service.analyze_food_image(file)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify({"error": result["error"]}), 500
    
    except Exception as e:
        print(f"Error analyzing image: {str(e)}")
        return jsonify({"error": str(e)}), 500
    


@food_routes.route('/capture', methods=['GET'])
def capture():
    """Render the food capture page with camera functionality"""
    return render_template('food_capture.html')

from datetime import datetime

@food_routes.route('/')
def index():
    """Render the main food analyzer page"""
    return render_template('index.html')

@food_routes.route('/dashboard')
def dashboard():
    """Render the user dashboard page"""
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('dashboard.html', today=today)

@food_routes.route('/account')
def account():
    """Render the user account page"""
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('account.html', today=today)


    # Add this route to handle food logging

from flask import request, jsonify
import os
import traceback

# Make sure we have a database connection function
def get_db_connection():
    """Create and return a connection to the PostgreSQL database."""
    import psycopg2
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    conn.autocommit = True
    return conn

# Update your food_logs function:

# Update the food_logs function to use the correct column names

@food_routes.route('/api/food-logs', methods=['POST', 'GET'])
def food_logs():
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid token'}), 401
    
    token = auth_header.split(' ')[1]
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user ID from token
        cur.execute("""
            SELECT user_id FROM user_tokens WHERE token = %s
        """, (token,))
        
        result = cur.fetchone()
        if not result:
            return jsonify({'error': 'Invalid token'}), 401
            
        user_id = result[0]
        
        # First, check if food_logs table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'food_logs'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        # Create the table if it doesn't exist
        if not table_exists:
            print("Creating food_logs table...")
            cur.execute("""
                CREATE TABLE food_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    calories INTEGER,
                    protein FLOAT,
                    carbs FLOAT,
                    fats FLOAT, 
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        
        # Get the column names from the table
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'food_logs'
        """)
        
        columns = [row[0] for row in cur.fetchall()]
        print(f"Available columns in food_logs: {columns}")
        
        # For POST requests (adding new food log)
        if request.method == 'POST':
            print("Processing POST request to /api/food-logs")
            # Get food data from request
            data = request.get_json()
            print(f"Received data: {data}")
            
            # Map request data to database column names
            # Use the column names that exist in the table
            name_column = 'name' if 'name' in columns else 'food_name'
            protein_column = 'protein' if 'protein' in columns else 'protein_g'
            carbs_column = 'carbs' if 'carbs' in columns else 'carbs_g'
            fats_column = 'fats' if 'fats' in columns else 'fat_g'
            date_column = 'date_added' if 'date_added' in columns else 'log_date'
            
            # Build the insert query dynamically based on available columns
            insert_columns = ['user_id', name_column, 'calories', protein_column, carbs_column, fats_column]
            values_placeholders = ['%s', '%s', '%s', '%s', '%s', '%s']
            
            if date_column in columns:
                insert_columns.append(date_column)
                values_placeholders.append('COALESCE(%s, NOW())')
            
            insert_query = f"""
                INSERT INTO food_logs 
                ({', '.join(insert_columns)}) 
                VALUES ({', '.join(values_placeholders)})
                RETURNING id
            """
            
            query_params = [
                user_id, 
                data.get('food_name', 'Unknown Food'),
                data.get('calories', 0),
                data.get('protein_g', 0),
                data.get('carbs_g', 0),
                data.get('fat_g', 0)
            ]
            
            if date_column in columns:
                query_params.append(data.get('log_date'))
                
            print(f"Executing insert: {insert_query} with params: {query_params}")
            cur.execute(insert_query, query_params)
            
            log_id = cur.fetchone()[0]
            conn.commit()
            
            print(f"Food log created with ID: {log_id}")
            
            # Return success response
            return jsonify({
                'message': 'Food logged successfully',
                'log_id': log_id
            }), 201
            
        # For GET requests (fetching food logs)
        else:
            # Construct the query based on available columns
            name_column = 'name' if 'name' in columns else 'food_name'
            protein_column = 'protein' if 'protein' in columns else 'protein_g'
            carbs_column = 'carbs' if 'carbs' in columns else 'carbs_g'
            fats_column = 'fats' if 'fats' in columns else 'fat_g'
            date_column = 'date_added' if 'date_added' in columns else 'log_date'
            
            # Build the select query with the correct column names
            query = f"""
                SELECT id, 
                       {name_column} AS food_name, 
                       calories, 
                       {protein_column} AS protein_g, 
                       {carbs_column} AS carbs_g, 
                       {fats_column} AS fat_g, 
                       {date_column} AS log_date
                FROM food_logs
                WHERE user_id = %s
                ORDER BY {date_column} DESC
            """
            
            print(f"Executing query: {query}")
            cur.execute(query, (user_id,))
            
            logs = []
            for row in cur.fetchall():
                log_data = {
                    'id': row[0],
                    'food_name': row[1] if row[1] else 'Unknown Food',
                    'calories': row[2] if row[2] is not None else 0,
                    'protein_g': row[3] if row[3] is not None else 0,
                    'carbs_g': row[4] if row[4] is not None else 0,
                    'fat_g': row[5] if row[5] is not None else 0
                }
                
                if len(row) > 6 and row[6]:
                    log_data['log_date'] = row[6].isoformat()
                
                logs.append(log_data)
            
            return jsonify({'logs': logs})
            
    except Exception as e:
        import traceback
        print(f"Error in food_logs endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()