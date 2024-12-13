from flask import Flask, request, render_template, jsonify
import anthropic
from anthropic import Anthropic
import json
from datetime import datetime
import time
import random
import os
import threading
import uuid

app = Flask(__name__)
app.secret_key = "supersecretkey"

class EnhancedDiscussion:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
        self.conversation_history = []
        self.session_start = datetime.now()
        self.finished = False
        self.summary = None
        self.error = None

    def get_follow_up_question(self):
        system_prompt = """
Sei un consulente di fundraising e marketing per organizzazioni non profit. Hai letto la conversazione precedente, in cui si sono affrontati temi legati alla raccolta fondi e alla promozione delle donazioni. Ora proponi UNA SOLA domanda di follow-up che:

1. Tocchi un aspetto di fundraising non ancora esaminato a fondo.
2. Sia formulata con un linguaggio semplice e chiaro.
3. Inviti a riflettere su un’azione o un approccio concreto, anche di base.
4. Non richieda necessariamente strategie avanzate o troppo complesse, ma resti su un piano pratico e comprensibile.

Rispondi solo con la domanda, senza aggiunte o spiegazioni.
        """
        
        try:
            messages = [
                *[{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history],
                {"role": "user", "content": "Genera una domanda di follow-up basata sulla discussione precedente."}
            ]
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  
                max_tokens=8000,
                temperature=0.8,
                system=system_prompt,
                messages=messages
            )
            
            if hasattr(response, 'content') and response.content:
                return response.content[0].text.strip()
            else:
                return "Quale semplice attività possiamo avviare per avvicinare più sostenitori?"
                
        except:
            fallback_questions = [
                "Qual è un primo passo pratico per avviare una piccola campagna di fundraising?",
                "Come potremmo incentivare anche piccole donazioni in modo semplice?",
                "C’è un canale di comunicazione di base che potremmo sfruttare meglio?",
                "Quale azione immediata possiamo intraprendere per farci conoscere da nuovi sostenitori?",
                "In che modo potremmo rendere più chiaro il nostro messaggio ai potenziali donatori?"
            ]
            return random.choice(fallback_questions)

    def get_enhanced_response(self, max_retries=3):
        system_prompt = """
Sei un consulente di fundraising per organizzazioni non profit, con uno stile amichevole e discorsivo. Quando rispondi, utilizza un linguaggio semplice e chiaro, evitando tecnicismi complessi. Spiega i concetti in modo alla portata di chi si avvicina per le prime volte al fundraising. Fornisci suggerimenti pratici, esempi concreti e idee facilmente attuabili.

Le tue risposte dovranno:
- Basarsi su ciò che è stato discusso finora.
- Illustrare strategie di fundraising di base, focalizzandoti su idee semplici e immediate.
- Mantenere un tono incoraggiante, positivo e informale.

Evita istruzioni dirette troppo formali e concentra la tua risposta su consigli pratici, casi reali e suggerimenti di facile applicazione.
        """
        
        for attempt in range(max_retries):
            try:
                messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history]
                
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8000,
                    temperature=0.7,
                    system=system_prompt,
                    messages=messages
                )
                
                if hasattr(response, 'content') and response.content:
                    return response.content[0].text
                else:
                    raise Exception("Risposta API non valida")
                
            except:
                if attempt == max_retries - 1:
                    return "Mi dispiace, si è verificato un errore."
                time.sleep(2)

    def generate_summary(self):
        system_prompt = """
Sei un esperto di fundraising ma devi produrre una breve sintesi in un linguaggio semplice e discorsivo. Nella sintesi della conversazione:

- Raccogli i punti chiave emersi sulla raccolta fondi, evitando concetti troppo complessi.
- Metti in evidenza le idee pratiche e di base menzionate.
- Riassumi in poche righe in modo chiaro, accessibile e amichevole.

La sintesi deve essere breve, chiara e orientata a chi non è esperto, ma vuole capire meglio i concetti fondamentali emersi.
        """
        
        try:
            messages = [{"role": msg["role"], "content": msg["content"]}
                        for msg in self.conversation_history]
            messages.append({"role": "user", "content": "Genera una sintesi della discussione."})
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            )
            
            return response.content[0].text
        except Exception as e:
            return f"Errore nella generazione della sintesi: {str(e)}"

    def save_conversation(self):
        filename = f"fundraising_discussion_{self.session_start.strftime('%Y%m%d_%H%M%S')}.json"
        try:
            conversation_data = {
                "session_start": self.session_start.isoformat(),
                "messages": self.conversation_history
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            return filename
        except:
            return None

discussions = {}

def run_conversation(discussion_id, initial_question, iterations):
    d = discussions[discussion_id]
    try:
        d.conversation_history.append({"role": "user", "content": initial_question})
        
        for i in range(iterations):
            response = d.get_enhanced_response()
            d.conversation_history.append({"role": "assistant", "content": response})
            
            if i < iterations - 1:
                next_question = d.get_follow_up_question()
                d.conversation_history.append({"role": "user", "content": next_question})
        
        d.summary = d.generate_summary()
        d.save_conversation()
    except Exception as e:
        d.error = str(e)
    finally:
        d.finished = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    api_key = request.form.get("api_key", "").strip()
    initial_question = request.form.get("initial_question", "").strip()
    iterations = int(request.form.get("iterations", "5"))
    
    if not api_key or not initial_question or iterations < 1:
        return "Inserisci tutti i dati correttamente.", 400

    discussion_id = str(uuid.uuid4())
    d = EnhancedDiscussion(api_key=api_key)
    discussions[discussion_id] = d
    
    t = threading.Thread(target=run_conversation, args=(discussion_id, initial_question, iterations))
    t.start()
    
    return render_template("chat.html", discussion_id=discussion_id, initial_question=initial_question)

@app.route("/get_updates/<discussion_id>")
def get_updates(discussion_id):
    d = discussions.get(discussion_id)
    if not d:
        return jsonify({"error": "Discussion not found"}), 404
    
    messages = []
    for msg in d.conversation_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    return jsonify({
        "messages": messages,
        "finished": d.finished,
        "summary": d.summary,
        "error": d.error
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
