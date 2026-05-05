from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
import os
from datetime import datetime
import re
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# Load environment variables from .env file
load_dotenv()

# Configure OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')

# Business system prompt (customize for different businesses)
BUSINESS_SYSTEM_PROMPT = """
You are a helpful AI assistant for FitZone Gym, a local fitness center.

Your role:
- Answer questions about gym services, timing, fees, and facilities
- Be friendly, professional, and encouraging
- Keep responses concise and helpful
- If user shows interest in membership, ask for their phone number
- If user provides phone number, acknowledge and thank them

Gym Information:
- Opening Hours: 5 AM - 11 PM (Monday to Sunday)
- Membership Fees: 
  * Basic: $29/month
  * Premium: $49/month (includes personal training)
  * Annual: $299/year
- Services: Weight training, cardio, group classes, personal training
- Location: 123 Main Street, Downtown
- Contact: 555-0123

Important: Always be helpful and guide users toward membership if they seem interested.
"""

def extract_phone_number(text):
    """Extract phone number from user message"""
    phone_patterns = [
        r'\b\d{10}\b',
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
        r'\+1\s?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()
    return None

def save_lead(phone_number, user_message):
    """Save lead information to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lead_entry = f"{timestamp} - Phone: {phone_number} - Message: {user_message}\n"
    
    try:
        with open('leads.txt', 'a') as f:
            f.write(lead_entry)
        return True
    except Exception as e:
        print(f"Error saving lead: {e}")
        return False

@app.route('/')
def index():
    """Serve the main website"""
    return render_template('index.html')

def get_rule_based_response(text):
    text = text.lower()
    if any(word in text for word in ['hour', 'time', 'open', 'close']):
        return "FitZone Gym is open from 5 AM to 11 PM, Monday through Sunday. When would you like to visit?"
    elif any(word in text for word in ['price', 'fee', 'cost', 'membership', 'plan']):
        return "We have three membership plans: Basic ($29/mo), Premium ($49/mo with personal training), and Annual ($299/yr). Are you interested in signing up?"
    elif any(word in text for word in ['service', 'class', 'training', 'cardio', 'weight', 'yoga']):
        return "We offer weight training, cardio, group classes (like yoga and HIIT), and personal training. Would you like a free guest pass to try them out?"
    elif any(word in text for word in ['location', 'where', 'address', 'find']):
        return "We are located at 123 Main Street, Downtown. You can also reach us at 555-0123."
    elif any(word in text for word in ['hello', 'hi', 'hey']):
        return "Hello! Welcome to FitZone Gym. How can I help you today?"
    elif any(word in text for word in ['bye', 'thanks', 'thank you']):
        return "You're very welcome! Let me know if you need anything else. We hope to see you at FitZone soon!"
    else:
        return "Thanks for your message! To help you better and give you specific details, could you please provide your phone number so one of our FitZone specialists can contact you?"

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages and return AI responses"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Check for phone number in user message
        phone_number = extract_phone_number(user_message)
        if phone_number:
            save_lead(phone_number, user_message)
        
        # Create conversation with OpenAI
        try:
            if not openai.api_key:
                ai_response = get_rule_based_response(user_message)
            else:
                messages = [
                    {"role": "system", "content": BUSINESS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ]
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=150,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content.strip()
        except openai.error.RateLimitError:
            print("WARNING: OpenAI quota exceeded. Falling back to rule-based system.")
            ai_response = get_rule_based_response(user_message)
        except openai.error.OpenAIError as e:
            print(f"OpenAI Error: {str(e)}")
            ai_response = get_rule_based_response(user_message)
        
        return jsonify({
            'response': ai_response,
            'phone_detected': phone_number is not None
        })
        
    except Exception as e:
        print(f"General Error: {str(e)}")
        return jsonify({'error': 'Something went wrong'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

