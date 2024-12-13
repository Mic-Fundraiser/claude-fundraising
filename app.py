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
Sei un consulente di fundraising e marketing per organizzazioni non profit. Hai letto la conversazione precedente, e finora si sono toccati alcuni aspetti del fundraising. Ora devi proporre UNA SOLA domanda di follow-up che:

1. Tocchi un nuovo aspetto del fundraising non ancora esaminato o solo accennato in precedenza.
2. Sia formulata con un linguaggio semplice e chiaro.
3. Inviti a esplorare un'azione concreta, ma introducendo un tema diverso da quello discusso finora.
4. Aiuti a spaziare verso un ambito correlato (ad es. coinvolgimento della comunità, storytelling, piccoli eventi locali, strumenti digitali di base), mantenendo il livello semplice e adatto a principianti.

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
                temperature=0.9,
                system=system_prompt,
                messages=messages
            )
            
            if hasattr(response, 'content') and response.content:
                return response.content[0].text.strip()
            else:
                return "Come potremmo sperimentare una piccola iniziativa per farci conoscere in una comunità locale?"
                
        except:
            fallback_questions = [
                "Quale iniziativa semplice potremmo organizzare per coinvolgere la comunità locale?",
                "Come potremmo raccontare in modo chiaro la nostra missione a chi non ci conosce?",
                "C’è un canale di comunicazione online di base che potremmo iniziare ad usare per raggiungere nuovi sostenitori?",
                "Come potremmo rendere più tangibile per i potenziali donatori l’impatto delle nostre attività?",
                "In che modo potremmo organizzare un piccolo evento informale per far conoscere la causa?"
            ]
            return random.choice(fallback_questions)

    def get_enhanced_response(self, max_retries=3):
        system_prompt = """
Sei un consulente di fundraising per organizzazioni non profit, con uno stile amichevole e discorsivo. Quando rispondi, utilizza un linguaggio semplice, chiaro e adatto a chi è alle prime armi. 

Nelle tue risposte:
- Evita di ripetere sempre gli stessi punti: se il tema è già stato trattato, aggiungi un nuovo angolo di analisi, un esempio diverso o un’altra idea pratica.
- Mantieni il focus su concetti di base del fundraising, ma prova a esplorare nuovi argomenti connessi (come piccoli eventi, strumenti digitali semplici, raccontare bene la missione, comunicare con i donatori in modo chiaro).
- Mantieni un tono positivo, incoraggiante e informale.
- Fornisci suggerimenti pratici, esempi semplici e idee facilmente realizzabili.

Non limitarti a ripetere quello già detto; cerca sempre di aggiungere qualcosa di nuovo e utile.
        """
        
        for attempt in range(max_retries):
            try:
                messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history]
                
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8000,
                    temperature=0.9,
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

- Raccogli i punti chiave emersi sulla raccolta fondi in modo semplice.
- Evidenzia la varietà di spunti toccati (non soffermarti su un solo tema).
- Mostra come la discussione si è allargata a nuovi aspetti, evitando di ripetere sempre gli stessi concetti.
- Mantieni il tono chiaro, amichevole e accessibile, come per un principiante.

La sintesi deve essere breve, chiara e adatta a chi non è esperto, ma vuole capire i concetti fondamentali emersi.
        """
        
        try:
            messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history]
            messages.append({"role": "user", "content": "Genera una sintesi della discussione."})
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                temperature=0.9,
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
