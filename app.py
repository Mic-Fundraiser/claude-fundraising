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

    def get_points_list(self):
        # Prompt per ottenere la lista di punti fondamentali
        system_prompt = """
Sei un consulente specializzato in fundraising per organizzazioni non profit. L'utente è alle prime armi e desidera capire come avviare una piccola campagna di raccolta fondi.

Il tuo compito è:
1. Leggere la richiesta e produrre una lista di 5-7 punti fondamentali da considerare per iniziare una piccola iniziativa di fundraising.
2. I punti devono essere semplici, chiari, tutti strettamente legati al fundraising, e non troppo complessi.
3. Non approfondire i singoli punti ora, limitati ad elencarli brevemente.

Rispondi solo con la lista dei punti (ad esempio con un elenco puntato) senza introdurre testo aggiuntivo.
        """

        try:
            # Costruiamo i messaggi da passare all'API
            messages = [
                # La conversazione finora
                *[{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history],
                # L'utente chiede la lista di punti
                {"role": "user", "content": "Potresti fornirmi una lista di punti chiave su come avviare una piccola iniziativa di fundraising?"}
            ]

            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=8000,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            )

            # Estrai il testo della risposta
            if hasattr(response, 'content') and response.content:
                list_text = response.content[0].text.strip()
                return self._parse_points(list_text)
            else:
                return ["Definire un obiettivo chiaro", "Identificare il pubblico dei donatori", "Scegliere un canale semplice per raccogliere fondi", "Creare un messaggio breve ed efficace", "Promuovere la campagna con mezzi di base", "Ringraziare e aggiornare i donatori"]
        
        except Exception as e:
            self.error = str(e)
            return []

    def get_point_detail(self, point):
        # Prompt per approfondire un singolo punto
        system_prompt = f"""
Sei un consulente specializzato in fundraising per organizzazioni non profit. Ora devi approfondire il seguente aspetto:

[PUNTO: "{point}"]

Spiega in modo semplice e adatto a un principiante:
- Perché questo aspetto è importante nel contesto del fundraising.
- Come metterlo in pratica in modo chiaro e concreto.
- Alcuni consigli utili per partire.

Non divagare su altri punti: concentrati solo su questo aspetto del fundraising, mantieni un tono semplice, concreto e strettamente legato al fundraising.
        """

        try:
            messages = [
                *[{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history],
                {"role": "user", "content": f"Approfondisci il seguente punto: {point}"}
            ]

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            )

            if hasattr(response, 'content') and response.content:
                return response.content[0].text.strip()
            else:
                return "Mi dispiace, non sono riuscito ad approfondire questo punto."
        
        except Exception as e:
            return f"Errore durante l'approfondimento: {str(e)}"

    def generate_summary(self):
        system_prompt = """
Sei un esperto di fundraising e devi produrre una breve sintesi della discussione in un linguaggio semplice.

Nella sintesi:
- Riassumi i punti chiave emersi sul fundraising in modo chiaro e comprensibile per un principiante.
- Mostra come la conversazione ha toccato diversi aspetti del fundraising (obiettivo chiaro, identificazione del pubblico, canali semplici, comunicazione efficace, piccoli eventi, ringraziamenti ai donatori, ecc.).
- Mantieni un tono amichevole, semplice e coerente, restando strettamente sul tema del fundraising.
La sintesi deve essere breve e utile.
        """
        
        try:
            messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history]
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

    def _parse_points(self, text):
        # Una funzione semplice per estrarre i punti elenco dalla risposta
        lines = text.split('\n')
        points = []
        for line in lines:
            # Rimuovi eventuali trattini o asterischi
            line = line.strip("-•* ").strip()
            if line:
                points.append(line)
        return points

discussions = {}

def run_conversation(discussion_id, initial_question, iterations):
    d = discussions[discussion_id]
    try:
        # 1. Aggiungi la domanda iniziale dell'utente
        d.conversation_history.append({"role": "user", "content": initial_question})
        
        # 2. Prima chiamata: ottieni la lista di punti
        points = d.get_points_list()
        d.conversation_history.append({"role": "assistant", "content": "\n".join(points)})
        
        # 3. Approfondisci i punti uno per uno, fino a 'iterations' o alla fine della lista
        max_points = min(iterations, len(points))
        for i in range(max_points):
            point = points[i]
            detail = d.get_point_detail(point)
            d.conversation_history.append({"role": "assistant", "content": detail})
        
        # 4. Genera la sintesi finale
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
