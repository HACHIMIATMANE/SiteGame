from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from deepface import DeepFace
import os
import pymongo
import cv2
from werkzeug.security import generate_password_hash, check_password_hash
import gridfs 
from deepface import DeepFace

from utils.email_service import EmailService
from dotenv import load_dotenv
import os

from functools import wraps


from werkzeug.utils import secure_filename


from utils.face_verification import verify_identity



import pymongo  # Add MongoDB support


from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest
import paypalrestsdk


import pandas as pd
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM



from datetime import datetime





# Load the Flan-T5 model
tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")

load_dotenv()

email_service = EmailService()

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'your-email@gmail.com')


# PayPal Configuration
PAYPAL_CLIENT_ID = 'ARHzz3f0k7fombqs4gtyth216HjO9J-K2lZ2kouhNLSTGFgIUEYi2lGVSxwz4UnFmVZeaIabyarHOPhg'
PAYPAL_CLIENT_SECRET = 'EG1G5CyijIk6YgnpjyUd2C9da_89sUS2YrtzT6f7fCW9PCb6-6u930H6Mx0JB6p58IbktAng3VN31zoy'

# Set up PayPal environment
paypal_client = PayPalHttpClient(SandboxEnvironment(
    client_id=PAYPAL_CLIENT_ID, 
    client_secret=PAYPAL_CLIENT_SECRET
))

# MongoDB configuration
client = pymongo.MongoClient("mongodb://localhost:27017/")  # Adjust this to your MongoDB URI
db = client["Flask"]  # Create or access the database
users_collection = db["users"]  # Create or access the collection for users
buyers_collection = db["sellers"]
fs = gridfs.GridFS(db)  # Create a GridFS object for file storage
chats_collection = db["chats"]



UPLOAD_FOLDER = 'productsimages'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' # Changez ceci pour une clé plus sécurisée
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from bson import ObjectId

from graphviz import render
import cv2
import re
import requests



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Format the email message
        email_body = f"""
        New contact form submission:
        
        From: {name} ({email})
        Subject: {subject}
        
        Message:
        {message}
        """

        # Send email
        success, message = email_service.send_message(
            sender=ADMIN_EMAIL,
            to=ADMIN_EMAIL,
            subject=f"Contact Form: {subject}",
            message_text=email_body
        )

        if success:
            flash('Your message has been sent successfully!', 'success')
        else:
            flash('There was an error sending your message. Please try again later.', 'error')
        
        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/product')
def product():
    return render_template('product.html')

@app.route('/productDetails')   
def productDetails():
    return render_template('productDetails.html')

@app.route('/productDetails1')   
def productDetails1():
    return render_template('productDetails1.html')

@app.route('/productDetails2')   
def productDetails2():
    return render_template('productDetails2.html')

@app.route('/productDetails3')   
def productDetails3():
    return render_template('productDetails3.html')



@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('signin'))

        # Chercher l'utilisateur dans MongoDB
        user = users_collection.find_one({"email": email})

        if user and check_password_hash(user['password'], password):
            # Stocker les informations utilisateur dans la session
            session['user_id'] = str(user['_id'])  # Convertir l'ID MongoDB en chaîne
            session['user_name'] = user['name']
            flash(f"Welcome, {user['name']}!", 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('signin'))

    return render_template('signin.html')





@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        user = {
            "name": name,
            "email": email,
            "password": hashed_password
        }
        users_collection.insert_one(user)

        flash('You have successfully signed up! Please log in.')
        return redirect(url_for('signin'))
        
    return render_template('signup.html')





@app.route('/admin_product', methods=['GET', 'POST'])
def admin_products():
    if request.method == 'POST':
        name = request.form['name']
        genre = request.form['genre']
        account_level = int(request.form['account_level'])
        price = float(request.form['price'])
        price_debatable = 'price_debatable' in request.form
        photo = request.files['photo']
        
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
        else:
            photo_path = None
        
        product = {
            "name": name,
            "genre": genre,
            "account_level": account_level,
            "price": price,
            "price_debatable": price_debatable,
            "photo_path": photo_path
        }
        
        db["products"].insert_one(product)
        flash('Product added successfully!')
        return redirect(url_for('admin_products'))
    
    products = db["products"].find()
    return render_template('admin_products.html', products=products)

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        # Fetch user purchases and sales from MongoDB
        purchases = db["purchases"].find({"_id": ObjectId(user_id)})
        sales = db["sales"].find({"_id": ObjectId(user_id)})
        
        # Convert cursor to list
        purchases_list = list(purchases)
        sales_list = list(sales)
        
        return render_template('dashboard.html', purchases=purchases_list, sales=sales_list)
    else:
        return redirect(url_for('verify'))


@app.route('/authenticate', methods=['POST'])
def authenticate():
    try:
        # Récupérer les données du formulaire
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        

        

   

        

        
            # Enregistrer les données de l'utilisateur dans MongoDB
        buyer_data = {
                "name": name,
                "email": email,
                "password": password,  # Note : hachez le mot de passe dans une vraie application
                
            }
        buyers_collection.insert_one(buyer_data)
        return redirect(url_for('verify'))
    

    except Exception as e:
        
        return str(e), 500

  

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password or not name:
            flash('Name, Email and password are required', 'error')
            return redirect(url_for('login'))            
        
        # Chercher l'utilisateur dans MongoDB
        # Chercher l'utilisateur dans MongoDB
        user = users_collection.find_one({"email": email})

        
       
        buyers_collection.insert_one(user)
      

        if user and check_password_hash(user['password'], password):
            # Stocker les informations utilisateur dans la session
            session['user_id'] = str(user['_id'])  # Convertir l'ID MongoDB en chaîne
            session['user_name'] = user['name']
            flash(f"Welcome, {user['name']}!", 'success')
            return redirect(url_for('verify'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')
   
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    return render_template('logout.html')  # Render the logout page


@app.route('/checkout')
def checkout():
    return render_template('checkout.html', 
                         paypal_client_id=PAYPAL_CLIENT_ID)

@app.route('/checkout1')
def checkout1():
    return render_template('checkout1.html',paypal_client_id=PAYPAL_CLIENT_ID)

@app.route('/checkout2')
def checkout2():
    return render_template('checkout2.html',paypal_client_id=PAYPAL_CLIENT_ID)

@app.route('/checkout3')
def checkout3():
    return render_template('checkout3.html', paypal_client_id=PAYPAL_CLIENT_ID)                                               




@app.route('/create-paypal-order', methods=['POST'])
def create_paypal_order():
    try:
        order_data = request.get_json()
        total_price = order_data.get('total', 10.00)
        
        request_body = OrdersCreateRequest()
        request_body.prefer('return=representation')
        request_body.request_body({
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(total_price)
                }
            }]
        })
        
        response = paypal_client.execute(request_body)
        return jsonify({
            'id': response.result.id
        })
    except Exception as e:
        print(f"Error creating order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/capture-paypal-order', methods=['POST'])
def capture_paypal_order():
    try:
        order_data = request.get_json()
        order_id = order_data.get('orderID')
        
        if not order_id:
            return jsonify({'error': 'Order ID is required'}), 400
        
        request_body = OrdersCaptureRequest(order_id)
        response = paypal_client.execute(request_body)
        
        return jsonify({
            'status': response.result.status,
            'order_details': response.result.dict()
        })
    except Exception as e:
        print(f"Error capturing order: {e}")
        return jsonify({'error': str(e)}), 500



# Load the Excel file
file_path = "games.xlsx"
try:
    games_data = pd.read_excel(file_path)
except Exception as e:
    print(f"Error loading games.xlsx: {e}")
    games_data = pd.DataFrame(columns=['game name', 'genre', 'Account lvl', 'price $', 'price debatable ?'])

def format_game_data(df):
    """Format game data for display"""
    formatted_games = []
    for _, row in df.iterrows():
        game = {
            "name": str(row['game name']),
            "genre": str(row['genre']),
            "level": str(row['Account lvl']),
            "price": float(row['price $']),
            "negotiable": bool(row['price debatable ?'])
        }
        formatted_games.append(game)
    return formatted_games

def handle_query(prompt, user_id=None):
    """Handle chat queries about game accounts"""
    prompt_lower = prompt.lower()
    
    # Greeting responses
    greetings = ["hello", "hi", "hey", "greetings"]
    if any(greet in prompt_lower for greet in greetings):
        return {
            "type": "text",
            "content": "Welcome to ShopAcc! How can we assist you today?"
        }
    
    # Price-related keywords
    price_keywords = ["below", "under", "less than", "more than", "above"]
    
    def extract_price(prompt):
        for keyword in price_keywords:
            if keyword in prompt.lower():
                price_part = prompt.lower().split(keyword)[-1].strip().replace("$", "").strip()
                try:
                    return keyword, int(price_part)
                except ValueError:
                    return None, None
        return None, None
    
    def find_matches(games_df, game_name=None, genre=None, price_op=None, price=None):
        matches = games_df.copy()
        if game_name:
            matches = matches[matches['game name'].str.contains(game_name, case=False, na=False)]
        if genre:
            matches = matches[matches['genre'].str.contains(genre, case=False, na=False)]
        if price_op and price is not None:
            if price_op in ["below", "under", "less than"]:
                matches = matches[matches['price $'] < price]
            elif price_op in ["more than", "above"]:
                matches = matches[matches['price $'] > price]
        return matches

    # Check for specific game or genre
    response_data = None
    message = ""

    try:
        # Game specific search
        for game_name in games_data["game name"].unique():
            if game_name.lower() in prompt_lower:
                price_op, price = extract_price(prompt)
                matching_games = find_matches(games_data, game_name=game_name, price_op=price_op, price=price)
                if not matching_games.empty:
                    message = f"Here are the available {game_name} accounts"
                    if price_op and price:
                        message += f" priced {price_op} ${price}"
                    response_data = format_game_data(matching_games)
                else:
                    message = f"No {game_name} accounts found"
                    if price_op and price:
                        message += f" priced {price_op} ${price}"
                break

        # Genre search if no game found
        if not response_data:
            for genre in games_data["genre"].unique():
                if genre.lower() in prompt_lower:
                    price_op, price = extract_price(prompt)
                    matching_games = find_matches(games_data, genre=genre, price_op=price_op, price=price)
                    if not matching_games.empty:
                        message = f"Here are the available {genre} accounts"
                        if price_op and price:
                            message += f" priced {price_op} ${price}"
                        response_data = format_game_data(matching_games)
                    else:
                        message = f"No {genre} accounts found"
                        if price_op and price:
                            message += f" priced {price_op} ${price}"
                    break

        # General price query if no specific game or genre found
        if not response_data:
            price_op, price = extract_price(prompt)
            if price_op and price is not None:
                matching_games = find_matches(games_data, price_op=price_op, price=price)
                if not matching_games.empty:
                    message = f"Here are all accounts priced {price_op} ${price}"
                    response_data = format_game_data(matching_games)
                else:
                    message = f"No accounts found priced {price_op} ${price}"

        if response_data:
            return {
                "type": "game_data",
                "message": message,
                "content": response_data
            }
        
        return {
            "type": "text",
            "content": "Sorry, we couldn't understand your query. Please ask about specific games, genres, or prices."
        }
    except Exception as e:
        print(f"Error in handle_query: {e}")
        return {
            "type": "text",
            "content": "Sorry, we encountered an error processing your request. Please try again."
        }


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_message = data.get('message')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        user_id = session.get('user_id')
        
        # Get username for the chat
        username = 'Anonymous'
        if user_id:
            user = users_collection.find_one({"_id": user_id})
            if user:
                username = user.get('name', 'Anonymous')
        else:
            # Get the next available anonymous user number
            try:
                last_anon = chats_collection.find_one(
                    {"username": {"$regex": "^user\\d+$"}},
                    sort=[("username", -1)]
                )
                if last_anon:
                    last_num = int(last_anon['username'].replace('user', ''))
                    username = f"user{last_num + 1}"
                else:
                    username = "user1"
            except Exception as e:
                print(f"Error getting anonymous username: {e}")
                username = "anonymous"

        # Get chatbot response
        response = handle_query(user_message, user_id)
        
        # Save conversation to MongoDB
        try:
            chat_entry = {
                "username": username,
                "user_id": user_id,
                "message": user_message,
                "response": response,
                "timestamp": datetime.utcnow()
            }
            chats_collection.insert_one(chat_entry)
        except Exception as e:
            print(f"Error saving chat to MongoDB: {e}")

        return jsonify({
            'response': response,
            'username': username
        })
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            'response': {
                'type': 'text',
                'content': 'Sorry, an error occurred. Please try again.'
            }
        }), 500

UPLOAD_FOLDER = 'temp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        if 'selfie' not in request.files or 'id_card' not in request.files:
            flash('Both selfie and ID card are required', 'error')
            return redirect(request.url)

        selfie = request.files['selfie']
        id_card = request.files['id_card']

        if selfie.filename == '' or id_card.filename == '':
            flash('No selected files', 'error')
            return redirect(request.url)

        if selfie and id_card and allowed_file(selfie.filename) and allowed_file(id_card.filename):
            # Create temp directory if it doesn't exist
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            # Save uploaded files
            selfie_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(selfie.filename))
            id_card_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(id_card.filename))
            
            selfie.save(selfie_path)
            id_card.save(id_card_path)

            try:
                # Verify identity
                result = verify_identity(selfie_path, id_card_path)

                # Clean up uploaded files
                os.remove(selfie_path)
                os.remove(id_card_path)

                if result['verified']:
                    flash('Identity verified successfully!', 'success')
                    return render_template(('dashboard.html'))
                else:
                    flash("The image doesn't match the one on the Id_Card ", 'error')
                    return render_template('verify.html')

            except Exception as e:
                flash(f'An error occurred: {str(e)}', 'error')
                return render_template('verify.html')

    return render_template('verify.html')


if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    if not os.path.exists(os.path.join(app.root_path, 'temp')):
        os.makedirs(os.path.join(app.root_path, 'temp'))
    app.run(debug=True)
    
