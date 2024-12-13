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
Sei un consulente specializzato in fundraising per organizzazioni non profit. Hai analizzato la conversazione precedente in cui si è parlato di vari aspetti di raccolta fondi. Ora devi proporre UNA SOLA domanda di follow-up che:

1. Tocchi un aspetto del fundraising non ancora affrontato in profondità (ad es. gestione dei piccoli donatori, semplice comunicazione della mission, organizzazione di un piccolo evento di raccolta fondi, strumenti base per raccogliere donazioni online, coinvolgimento di volontari, ecc.).
2. Utilizzi un linguaggio semplice e chiaro, adatto a principianti del settore.
3. Inviti a considerare una nuova azione concreta, ma sempre legata al fundraising.
4. Mantenga l’attenzione su aspetti pratici e di base del fundraising, senza uscire dal suo ambito.

Rispondi solo con la domanda, senza aggiungere spiegazioni o altro testo.
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
                return "Come potremmo coinvolgere piccoli donatori in modo semplice e continuativo?"
                
        except:
            fallback_questions = [
                "Come potremmo rendere più chiaro il nostro messaggio ai piccoli donatori?",
                "In che modo potremmo organizzare un piccolo evento di raccolta fondi semplice da gestire?",
                "Quale canale online di base potremmo usare per ricevere donazioni?",
                "Come potremmo mostrare meglio l’impatto delle donazioni ai potenziali sostenitori?",
                "C’è un modo facile per invitare volontari a supportare una piccola iniziativa di raccolta fondi?"
            ]
            return random.choice(fallback_questions)

    def get_enhanced_response(self, max_retries=3):
        system_prompt = """
Sei un consulente specializzato in fundraising per organizzazioni non profit. Utilizza uno stile amichevole e discorsivo, adatto a chi ha poca esperienza nel settore.

Nelle tue risposte:
- Rimani sempre focalizzato su temi strettamente legati al fundraising.
- Non ripetere sempre gli stessi consigli. Se una strategia è già stata trattata, aggiungi un nuovo punto di vista o un’altra idea semplice.
- Mantieni il linguaggio chiaro, non tecnico, e proponi suggerimenti facili da mettere in pratica per chi inizia.
- Mostra varietà di soluzioni (donazioni online semplici, piccoli eventi, comunicazione della mission, coinvolgimento della comunità, gestione di donatori ricorrenti, ecc.), sempre nel fundraising.
- Mantieni un tono positivo, incoraggiante e informale.

Evita di ripetere le stesse idee e cerca di arricchire la discussione con spunti nuovi ma semplici, senza uscire dal tema del fundraising.
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
Sei un esperto di fundraising e devi produrre una breve sintesi della discussione in un linguaggio semplice. Nella sintesi:

- Riassumi i punti chiave emersi sul fundraising in modo chiaro e comprensibile per un principiante.
- Evidenzia come la conversazione ha toccato diversi aspetti del fundraising (comunicare la mission, piccoli eventi, canali online semplici, coinvolgimento della comunità, donazioni ricorrenti, ecc.), senza soffermarsi su un solo tema.
- Mantieni un tono amichevole, semplice e coerente, restando strettamente sul tema del fundraising.

La sintesi deve essere breve, utile e facile da capire.
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
