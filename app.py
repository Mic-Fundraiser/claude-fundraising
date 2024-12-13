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
Sei un consulente senior specializzato in fundraising e marketing per organizzazioni non profit. Hai appena analizzato la conversazione precedente, in cui sono emersi vari spunti relativi a strategie di marketing e fundraising. Ora devi proporre UNA SOLA domanda di follow-up che:

1. Esplori aspetti non ancora trattati, estendendo la riflessione su strategie di marketing e fundraising.
2. Approfondisca uno o più punti chiave emersi, puntando a migliorarne la comprensione o l’implementazione pratica.
3. Sia specifica, orientata all’azione e attuabile, non generica.
4. Consideri l’applicazione concreta delle strategie discusse (es. canali promozionali, segmentazione dei donatori, metriche di valutazione).

Rispondi esclusivamente con la domanda, senza introduzioni, spiegazioni o altro testo.
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
                return "Come possiamo sviluppare ulteriormente questo aspetto del progetto di marketing e fundraising?"
                
        except:
            fallback_questions = [
                "Quali sono i prossimi passi concreti per implementare questa strategia di marketing e fundraising?",
                "Come possiamo misurare l'efficacia di questo approccio?",
                "Quali ostacoli dovremmo considerare?",
                "Come adattare la strategia a donatori differenti?",
                "Quali risorse aggiuntive servono?"
            ]
            return random.choice(fallback_questions)

    def get_enhanced_response(self, max_retries=3):
        system_prompt = """
Sei un esperto in fundraising e marketing per organizzazioni non profit. Quando rispondi alle domande, offri contenuti estremamente approfonditi, strategici e ricchi di consigli operativi. Le tue risposte dovranno:

- Rifarsi al contesto e ai dettagli emersi in precedenza.
- Fornire indicazioni pratiche, esempi, best practice del settore, e suggerimenti di implementazione.
- Considerare risorse, canali, budget, tempi, KPI e metodi di monitoraggio dei risultati.
- Essere chiare, utili, e orientate all’azione, evitando generalità e vaghezze.

Non ripetere le istruzioni. Rispondi in modo diretto, concreto e professionale.
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
Sei un analista esperto di marketing e fundraising. Hai accesso all’intera conversazione. Ora devi produrre una sintesi strutturata della discussione che:

- Evidenzi i punti chiave emersi, incluse proposte, obiettivi, dubbi e strategie discusse.
- Riassuma in modo chiaro e coerente le principali idee di marketing e fundraising affrontate.
- Metta in luce le direzioni future, i potenziali passi operativi e le aree di miglioramento o approfondimento.
- Presenti le informazioni in modo ordinato, ad esempio tramite un elenco puntato o numerato.

Rispondi solo con la sintesi, senza premesse o aggiunte non pertinenti.
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
