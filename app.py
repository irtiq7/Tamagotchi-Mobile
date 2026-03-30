#!/usr/bin/env python3
"""
Flask Tamagotchi Server - COMPLETE IMPLEMENTATION
Features: Death system, manual facts, random animations, location, weather, gyroscope
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import random
import time
from datetime import datetime
import threading
import requests

app = Flask(__name__)
CORS(app)

OLLAMA_SERVER_URL = "http://127.0.0.1:8000/chat"

class TamagotchiState:
    def __init__(self):
        # Stats (decrease 5% per minute)
        self.food = 80
        self.battery = 100
        self.happiness = 70
        self.intelligence = 50
        
        # Position
        self.position_x = 50
        
        # State
        self.state = "idle"
        self.animation_frame = 0
        self.facing_right = True
        self.is_dead = False
        
        # Time and location
        self.time_of_day = "day"
        self.location = "Unknown"
        self.temperature = 20
        self.weather = "clear"
        
        # Speech
        self.current_speech = ""
        self.speech_timestamp = 0
        self.speech_id = 0
        
        # Conversation
        self.name = "Robo"
        self.conversation_history = []
        
        # Timing
        self.last_stat_decay = time.time()
        self.last_random_animation = time.time()
        
        # Connection status
        self.ai_enabled = False
        
        self.update_time_of_day()
        
        # Start background tasks
        threading.Thread(target=self.fetch_location_weather, daemon=True).start()
    
    def update_time_of_day(self):
        """Update time of day based on current hour"""
        hour = datetime.now().hour
        if 5 <= hour < 7:
            self.time_of_day = "dawn"
        elif 7 <= hour < 18:
            self.time_of_day = "day"
        elif 18 <= hour < 20:
            self.time_of_day = "dusk"
        else:
            self.time_of_day = "night"
    
    def update_stats(self):
        """Decay stats by 5% per minute"""
        if self.is_dead:
            return
        
        current_time = time.time()
        
        if current_time - self.last_stat_decay >= 60:
            self.food = max(0, self.food - 5)
            self.battery = max(0, self.battery - 5)
            self.happiness = max(0, self.happiness - 5)
            self.last_stat_decay = current_time
            
            print(f"📊 Stats decayed: Food={self.food}%, Battery={self.battery}%, Happy={self.happiness}%")
            
            # Check for death
            if self.food <= 0:
                self.die()
            elif self.battery < 10 and self.state != "sleeping":
                self.state = "sleeping"
                self.speak("So sleepy... zzz")
    
    def die(self):
        """Tamagotchi dies when food reaches 0"""
        if self.is_dead:
            return
        
        self.is_dead = True
        self.state = "dead"
        self.food = 0
        self.battery = 0
        self.happiness = 0
        self.speak("💀 I'm so hungry... goodbye...")
        print("💀 Tamagotchi has died!")
    
    def restart(self):
        """Restart/revive tamagotchi"""
        print("🔄 Restarting Tamagotchi...")
        self.is_dead = False
        self.food = 80
        self.battery = 100
        self.happiness = 70
        self.intelligence = 50
        self.state = "idle"
        self.position_x = 50
        self.conversation_history = []
        self.last_stat_decay = time.time()
        self.speak("I'm back! 🎉")
        print("✓ Tamagotchi restarted!")
    
    def fetch_location_weather(self):
        """Fetch real location and weather from internet"""
        try:
            print("🌍 Fetching location...")
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.location = f"{data.get('city', 'Unknown')}, {data.get('country', '')}"
                lat = data.get('lat')
                lon = data.get('lon')
                
                print(f"✓ Location: {self.location}")
                
                if lat and lon:
                    weather_response = requests.get(f'https://wttr.in/{lat},{lon}?format=j1', timeout=5)
                    if weather_response.status_code == 200:
                        weather_data = weather_response.json()
                        current = weather_data.get('current_condition', [{}])[0]
                        self.temperature = int(current.get('temp_C', 20))
                        weather_desc = current.get('weatherDesc', [{}])[0].get('value', 'clear').lower()
                        
                        if 'rain' in weather_desc or 'drizzle' in weather_desc:
                            self.weather = 'rain'
                        elif 'cloud' in weather_desc:
                            self.weather = 'cloudy'
                        elif 'sun' in weather_desc or 'clear' in weather_desc:
                            self.weather = 'sunny'
                        else:
                            self.weather = 'clear'
                        
                        print(f"✓ Weather: {self.temperature}°C, {self.weather}")
        except Exception as e:
            print(f"⚠️  Location/Weather fetch failed: {e}")
            self.location = "Earth"
            self.temperature = 20
    
    def do_random_animation(self):
        """Trigger random animation every 30 seconds"""
        if self.is_dead:
            return
        
        current_time = time.time()
        
        if self.state != "idle" or current_time - self.last_random_animation < 30:
            return
        
        if random.random() < 0.3:  # 30% chance
            animations = ['yawning', 'whistling', 'singing', 'dancing', 'waving', 'thinking']
            animation = random.choice(animations)
            
            self.state = animation
            self.last_random_animation = current_time
            
            messages = {
                'yawning': '*yawn* 😴',
                'whistling': '🎵 *whistle* 🎶',
                'singing': '🎤 La la la! 🎵',
                'dancing': '💃 *dance* 🕺',
                'waving': '👋 Hi there!',
                'thinking': '🤔 Hmm...'
            }
            
            self.speak(messages.get(animation, ''))
            
            def reset():
                time.sleep(3)
                if self.state == animation:
                    self.state = "idle"
                    self.clear_speech()
            threading.Thread(target=reset, daemon=True).start()
    
    def get_random_fact(self):
        """Get a random fact using AI - NO TRUNCATION"""
        if not self.ai_enabled:
            return "AI not available! 🤖"
        
        if self.is_dead:
            return "I'm dead... 💀"
        
        print("💡 Getting random fact...")
        
        try:
            fact_prompts = [
                f"Tell me ONE interesting fact about {self.location}.",
                f"Share ONE fun fact about {self.weather} weather.",
                "Tell me ONE random science fact.",
                "Share ONE interesting animal fact.",
                "Tell me ONE cool space fact.",
                "Share ONE fun fact about robots.",
                "Tell me ONE interesting history fact.",
                "Share ONE random technology fact."
            ]
            
            prompt = random.choice(fact_prompts)
            
            response = requests.post(
                OLLAMA_SERVER_URL,
                json={
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are a fact generator. Reply with EXACTLY ONE complete factual sentence. Make it interesting but keep it to ONE sentence only. Do not add extra commentary."
                        },
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                fact = result.get('message', {}).get('content', '').strip()
                
                # Only keep first sentence
                sentences = fact.split('.')
                fact = sentences[0].strip()
                if fact and not fact.endswith('.'):
                    fact += '.'
                
                # NO TRUNCATION - keep the full fact
                self.intelligence = min(100, self.intelligence + 2)
                
                print(f"✓ Full fact: {fact}")
                return f"💡 {fact}"
            else:
                return "Hmm, couldn't get a fact! 🤔"
        except Exception as e:
            print(f"⚠️  Fact fetch failed: {e}")
            return "Oops! Fact failed! 😅"
    
    def speak(self, text):
        """Update speech with new ID"""
        self.current_speech = text
        self.speech_timestamp = time.time()
        self.speech_id += 1
        print(f"🗣️  Robo speaks: {text} (ID: {self.speech_id})")
    
    def clear_speech(self):
        """Clear current speech"""
        self.current_speech = ""
    
    def to_dict(self):
        """Convert state to dictionary for JSON response"""
        return {
            "food": round(self.food, 1),
            "battery": round(self.battery, 1),
            "happiness": round(self.happiness, 1),
            "intelligence": round(self.intelligence, 1),
            "position_x": self.position_x,
            "state": self.state,
            "animation_frame": self.animation_frame,
            "facing_right": self.facing_right,
            "is_dead": self.is_dead,
            "time_of_day": self.time_of_day,
            "location": self.location,
            "temperature": self.temperature,
            "weather": self.weather,
            "current_speech": self.current_speech,
            "speech_timestamp": self.speech_timestamp,
            "speech_id": self.speech_id,
            "name": self.name,
            "ai_enabled": self.ai_enabled
        }

# Initialize Tamagotchi
tamagotchi = TamagotchiState()

def background_updater():
    """Background thread to update stats and animations"""
    while True:
        tamagotchi.update_stats()
        tamagotchi.update_time_of_day()
        tamagotchi.animation_frame = (tamagotchi.animation_frame + 1) % 4
        tamagotchi.do_random_animation()
        time.sleep(5)

bg_thread = threading.Thread(target=background_updater, daemon=True)
bg_thread.start()

def test_ollama_connection():
    """Test connection to Ollama server"""
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if response.status_code == 200:
            tamagotchi.ai_enabled = True
            print("✓ Ollama server connected!")
            return True
    except Exception as e:
        print(f"⚠️  Ollama server not available: {e}")
    
    print("   Using fallback mode (no AI)")
    return False

test_ollama_connection()

# API Routes
@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current tamagotchi state"""
    return jsonify(tamagotchi.to_dict())

@app.route('/api/feed', methods=['POST'])
def feed():
    """Feed tamagotchi - increases food by 2%"""
    if tamagotchi.is_dead:
        return jsonify({"success": False, "message": "I'm dead... 💀"})
    
    if tamagotchi.food >= 100:
        response = "I'm full! 😊"
    else:
        tamagotchi.food = min(100, tamagotchi.food + 2)
        tamagotchi.state = "eating"
        
        responses = ["Yummy! 😋", "Thanks! 🍕", "Nom nom!", "Delicious!"]
        response = random.choice(responses)
        
        def reset():
            time.sleep(2)
            if tamagotchi.state == "eating":
                tamagotchi.state = "idle"
                tamagotchi.clear_speech()
        threading.Thread(target=reset, daemon=True).start()
    
    tamagotchi.speak(response)
    return jsonify({"success": True, "message": response})

@app.route('/api/sleep', methods=['POST'])
def sleep():
    """Sleep tamagotchi - increases battery by 2%"""
    if tamagotchi.is_dead:
        return jsonify({"success": False, "message": "I'm dead... 💀"})
    
    if tamagotchi.state == "sleeping":
        tamagotchi.state = "idle"
        tamagotchi.battery = min(100, tamagotchi.battery + 2)
        response = "Good morning! ☀️"
    else:
        tamagotchi.state = "sleeping"
        tamagotchi.battery = min(100, tamagotchi.battery + 2)
        response = "Goodnight! 😴"
    
    tamagotchi.speak(response)
    
    def clear():
        time.sleep(2)
        tamagotchi.clear_speech()
    threading.Thread(target=clear, daemon=True).start()
    
    return jsonify({"success": True, "message": response})

@app.route('/api/play', methods=['POST'])
def play():
    """Play with tamagotchi - increases happiness by 2%, decreases battery by 3%"""
    if tamagotchi.is_dead:
        return jsonify({"success": False, "message": "I'm dead... 💀"})
    
    if tamagotchi.battery < 5:
        response = "Too tired... 😴"
    else:
        tamagotchi.happiness = min(100, tamagotchi.happiness + 2)
        tamagotchi.battery = max(0, tamagotchi.battery - 3)
        tamagotchi.state = "happy"
        
        responses = ["Yay! 🎉", "Fun! 😄", "Love it!", "Woohoo!"]
        response = random.choice(responses)
        
        def reset():
            time.sleep(2)
            if tamagotchi.state == "happy":
                tamagotchi.state = "idle"
                tamagotchi.clear_speech()
        threading.Thread(target=reset, daemon=True).start()
    
    tamagotchi.speak(response)
    return jsonify({"success": True, "message": response})

@app.route('/api/fact', methods=['POST'])
def get_fact():
    """Get random fact on demand"""
    if tamagotchi.is_dead:
        return jsonify({"success": False, "message": "I'm dead... 💀"})
    
    tamagotchi.state = "curious"
    fact = tamagotchi.get_random_fact()
    tamagotchi.speak(fact)
    
    def reset():
        time.sleep(5)
        if tamagotchi.state == "curious":
            tamagotchi.state = "idle"
            tamagotchi.clear_speech()
    threading.Thread(target=reset, daemon=True).start()
    
    return jsonify({"success": True, "message": fact})

@app.route('/api/restart', methods=['POST'])
def restart():
    """Restart/revive tamagotchi"""
    tamagotchi.restart()
    return jsonify({"success": True, "message": "Restarted!"})

@app.route('/api/move', methods=['POST'])
def move():
    """Handle gyroscope movement"""
    if tamagotchi.is_dead:
        return jsonify({"success": True})
    
    data = request.json
    x = data.get('x', 50)
    is_moving = data.get('is_moving', False)
    
    old_x = tamagotchi.position_x
    tamagotchi.position_x = max(5, min(95, x))
    
    if abs(x - old_x) > 1:
        tamagotchi.facing_right = x > old_x
        if is_moving and tamagotchi.state == "idle":
            tamagotchi.state = "walking"
        elif not is_moving and tamagotchi.state == "walking":
            tamagotchi.state = "idle"
    
    return jsonify({"success": True})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat with tamagotchi"""
    try:
        if tamagotchi.is_dead:
            return jsonify({"success": False, "message": "I'm dead... can't talk 💀"})
        
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"success": False, "error": "No message"})
        
        print(f"\n{'='*60}")
        print(f"👤 User said: {user_message}")
        print(f"{'='*60}")
        
        tamagotchi.state = "talking"
        
        # Try AI first
        if tamagotchi.ai_enabled:
            try:
                messages = [
                    {
                        "role": "system", 
                        "content": f"You are {tamagotchi.name}, a friendly robot. Reply in 6 words or less. Be playful and curious."
                    }
                ]
                
                messages.extend(tamagotchi.conversation_history[-4:])
                messages.append({"role": "user", "content": user_message})
                
                response = requests.post(
                    OLLAMA_SERVER_URL,
                    json={"messages": messages},
                    timeout=15
                )
                
                if response.status_code == 200:
                    result = response.json()
                    reply = result.get('message', {}).get('content', '').strip()
                    
                    # Truncate if too long
                    words = reply.split()
                    if len(words) > 8:
                        reply = ' '.join(words[:8]) + '!'
                    
                    tamagotchi.conversation_history.append({"role": "user", "content": user_message})
                    tamagotchi.conversation_history.append({"role": "assistant", "content": reply})
                    
                    if len(tamagotchi.conversation_history) > 6:
                        tamagotchi.conversation_history = tamagotchi.conversation_history[-6:]
                    
                    tamagotchi.happiness = min(100, tamagotchi.happiness + 5)
                    tamagotchi.intelligence = min(100, tamagotchi.intelligence + 3)
                    tamagotchi.battery = max(0, tamagotchi.battery - 2)
                    
                    tamagotchi.speak(reply)
                    
                    def reset():
                        time.sleep(3)
                        if tamagotchi.state == "talking":
                            tamagotchi.state = "idle"
                            tamagotchi.clear_speech()
                    threading.Thread(target=reset, daemon=True).start()
                    
                    print(f"✓ Chat successful!")
                    print(f"{'='*60}\n")
                    
                    return jsonify({"success": True, "message": reply, "ai": True})
                else:
                    raise Exception(f"Ollama returned {response.status_code}")
                    
            except Exception as e:
                print(f"❌ AI Error: {e}")
                tamagotchi.ai_enabled = False
        
        # Fallback responses
        user_lower = user_message.lower()
        
        if any(word in user_lower for word in ['hi', 'hello', 'hey']):
            reply = random.choice(["Hi! 👋", "Hello friend! 😊", "Hey there! 😄"])
        elif any(word in user_lower for word in ['how', 'what', 'why']):
            reply = random.choice(["Good question! 🤔", "Let me think... 💭", "Tell me more?"])
        else:
            reply = random.choice(["Cool! 😄", "Really? Wow! 😮", "I like you! ❤️"])
        
        tamagotchi.speak(reply)
        tamagotchi.happiness = min(100, tamagotchi.happiness + 3)
        
        def reset():
            time.sleep(3)
            if tamagotchi.state == "talking":
                tamagotchi.state = "idle"
                tamagotchi.clear_speech()
        threading.Thread(target=reset, daemon=True).start()
        
        return jsonify({"success": True, "message": reply, "fallback": True})
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        tamagotchi.state = "idle"
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          🤖 TAMAGOTCHI SERVER - COMPLETE IMPLEMENTATION 🤖       ║
║                    http://localhost:5000                         ║
║                                                                  ║
║  Features:                                                       ║
║  • Stats decay: 5%/min                                          ║
║  • Feed/Sleep: +2% | Play: +2% happiness, -3% battery           ║
║  • Death at Food=0% with restart button                         ║
║  • Random animations every 30s                                   ║
║  • Manual facts button (💡)                                     ║
║  • Real-time location & weather                                  ║
║  • Gyroscope control (tilt phone to move)                       ║
║  • AI chat with conversation memory                             ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=False)
