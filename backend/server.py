from fastapi import FastAPI, APIRouter, HTTPException, File, UploadFile, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import base64
import asyncio
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    subscription_status: str = "trial"
    referral_code: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    discount_amount: float = 0.0
    preferred_language: str = "en"  # Default to English
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Recording(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    audio_data: str  # Base64 encoded audio
    transcript: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = []
    notes: str = ""
    duration: Optional[float] = None
    status: str = "uploaded"  # uploaded, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RecordingCreate(BaseModel):
    title: str
    audio_data: str
    tags: List[str] = []
    notes: str = ""
    duration: Optional[float] = None

class TranscriptionRequest(BaseModel):
    recording_id: str
    type: str = "full"  # full, summary, chapters
    language: str = "en"  # User's preferred language

class ProcessingResponse(BaseModel):
    message: str
    recording_id: str
    status: str

# Helper functions
async def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(security)):
    token = authorization.credentials
    session = await db.sessions.find_one({"session_token": token})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    
    session_obj = Session(**session)
    if session_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = await db.users.find_one({"id": session_obj.user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**user)

async def process_audio_with_ai(recording_id: str, audio_data: str, processing_type: str = "full", language: str = "en"):
    """Process audio data with language-specific mock AI responses"""
    try:
        # Language-specific content templates
        language_content = {
            "en": {
                "full": """Welcome to today's Physics lecture on Newton's Laws of Motion. 

Today we're going to explore the fundamental principles that govern how objects move and interact with forces. Let's start with Newton's First Law, also known as the Law of Inertia.

Newton's First Law states that an object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an external force. This might seem obvious, but it's actually quite profound when you think about it.

For example, if you're sitting in a car and the car suddenly stops, your body continues moving forward. This is because your body wants to maintain its state of motion - that's inertia in action.

Now, let's move on to Newton's Second Law, which is probably the most famous: F equals ma. Force equals mass times acceleration. This law tells us that the force applied to an object is directly proportional to the mass of the object and its acceleration.

A practical example: if you push a shopping cart with the same force, an empty cart will accelerate much faster than a full cart. Same force, different mass, different acceleration.

Finally, Newton's Third Law states that for every action, there is an equal and opposite reaction. When you walk, you push backward on the ground, and the ground pushes forward on you.

These three laws form the foundation of classical mechanics and help us understand motion in our everyday world. Next class, we'll explore how these laws apply to circular motion and gravity.""",
                "summary": """📚 **Physics Lecture Summary: Newton's Laws of Motion**

**🎯 Key Concepts:**
• **Newton's First Law (Law of Inertia)**: Objects maintain their state of motion unless acted upon by external forces
• **Newton's Second Law**: F = ma (Force = mass × acceleration)  
• **Newton's Third Law**: Every action has an equal and opposite reaction

**💡 Main Points:**
1. **Inertia explained**: Objects resist changes in motion - demonstrated by car stopping example
2. **Force-mass relationship**: Same force on different masses produces different accelerations (shopping cart example)
3. **Action-reaction pairs**: Walking involves pushing ground backward, ground pushes you forward

**🔍 Practical Examples:**
- Car stopping → body continues moving forward (inertia)
- Empty vs full shopping cart → different accelerations with same force
- Walking → action-reaction force pairs

**📖 Next Session Preview:**
Application of these laws to circular motion and gravitational forces

**⭐ Study Focus:**
Understand how these three fundamental laws explain everyday motion phenomena""",
                "chapters": """📖 **Lecture Structure: Newton's Laws of Motion**

**🎬 Introduction (0:00-2:30)**
- Course overview and today's topic
- Importance of Newton's Laws in physics

**📚 Chapter 1: Newton's First Law - Law of Inertia (2:30-8:45)**
- Definition and explanation
- Real-world examples (car stopping scenario)
- Understanding inertia in daily life

**⚖️ Chapter 2: Newton's Second Law - F=ma (8:45-15:20)**
- Mathematical relationship between force, mass, and acceleration
- Practical demonstration: shopping cart example
- Problem-solving applications

**🔄 Chapter 3: Newton's Third Law - Action-Reaction (15:20-22:10)**
- Equal and opposite reactions principle
- Walking as an example of action-reaction pairs
- Common misconceptions addressed

**🎯 Conclusion & Next Steps (22:10-25:00)**
- Summary of three laws
- Preview of next lecture: circular motion and gravity
- Study recommendations

**💡 Key Takeaways:**
Each law builds upon the previous one to create a complete understanding of motion dynamics"""
            },
            "it": {
                "full": """Benvenuti alla lezione di Fisica di oggi sulle Leggi del Moto di Newton.

Oggi esploreremo i principi fondamentali che governano come gli oggetti si muovono e interagiscono con le forze. Iniziamo con la Prima Legge di Newton, nota anche come Legge dell'Inerzia.

La Prima Legge di Newton afferma che un oggetto a riposo rimane a riposo, e un oggetto in movimento rimane in movimento a velocità costante, a meno che non sia soggetto a una forza esterna. Questo può sembrare ovvio, ma è in realtà molto profondo.

Ad esempio, se state seduti in una macchina e la macchina si ferma improvvisamente, il vostro corpo continua a muoversi in avanti. Questo perché il vostro corpo vuole mantenere il suo stato di moto - questa è l'inerzia in azione.

Ora, passiamo alla Seconda Legge di Newton, che è probabilmente la più famosa: F uguale ma. Forza uguale massa per accelerazione. Questa legge ci dice che la forza applicata a un oggetto è direttamente proporzionale alla massa dell'oggetto e alla sua accelerazione.

Un esempio pratico: se spingete un carrello della spesa con la stessa forza, un carrello vuoto accelererà molto più velocemente di un carrello pieno. Stessa forza, massa diversa, accelerazione diversa.

Infine, la Terza Legge di Newton afferma che per ogni azione, c'è una reazione uguale e opposta. Quando camminate, spingete all'indietro sul terreno, e il terreno spinge in avanti su di voi.

Queste tre leggi formano la base della meccanica classica e ci aiutano a comprendere il movimento nel nostro mondo quotidiano. La prossima lezione esploreremo come queste leggi si applicano al moto circolare e alla gravità.""",
                "summary": """📚 **Riassunto Lezione di Fisica: Leggi del Moto di Newton**

**🎯 Concetti Chiave:**
• **Prima Legge di Newton (Legge dell'Inerzia)**: Gli oggetti mantengono il loro stato di moto a meno che non siano soggetti a forze esterne
• **Seconda Legge di Newton**: F = ma (Forza = massa × accelerazione)
• **Terza Legge di Newton**: Ogni azione ha una reazione uguale e opposta

**💡 Punti Principali:**
1. **Inerzia spiegata**: Gli oggetti resistono ai cambiamenti nel moto - dimostrato dall'esempio dell'auto che si ferma
2. **Relazione forza-massa**: Stessa forza su masse diverse produce accelerazioni diverse (esempio carrello della spesa)
3. **Coppie azione-reazione**: Camminare implica spingere il terreno all'indietro, il terreno spinge in avanti

**🔍 Esempi Pratici:**
- Auto che si ferma → corpo continua a muoversi in avanti (inerzia)
- Carrello vuoto vs pieno → accelerazioni diverse con stessa forza
- Camminare → coppie di forze azione-reazione

**📖 Anteprima Prossima Sessione:**
Applicazione di queste leggi al moto circolare e alle forze gravitazionali

**⭐ Focus di Studio:**
Comprendere come queste tre leggi fondamentali spiegano i fenomeni di moto quotidiani""",
                "chapters": """📖 **Struttura della Lezione: Leggi del Moto di Newton**

**🎬 Introduzione (0:00-2:30)**
- Panoramica del corso e argomento di oggi
- Importanza delle Leggi di Newton nella fisica

**📚 Capitolo 1: Prima Legge di Newton - Legge dell'Inerzia (2:30-8:45)**
- Definizione e spiegazione
- Esempi del mondo reale (scenario auto che si ferma)
- Comprensione dell'inerzia nella vita quotidiana

**⚖️ Capitolo 2: Seconda Legge di Newton - F=ma (8:45-15:20)**
- Relazione matematica tra forza, massa e accelerazione
- Dimostrazione pratica: esempio del carrello della spesa
- Applicazioni nella risoluzione di problemi

**🔄 Capitolo 3: Terza Legge di Newton - Azione-Reazione (15:20-22:10)**
- Principio delle reazioni uguali e opposte
- Camminare come esempio di coppie azione-reazione
- Errori comuni affrontati

**🎯 Conclusione e Prossimi Passi (22:10-25:00)**
- Riassunto delle tre leggi
- Anteprima della prossima lezione: moto circolare e gravità
- Raccomandazioni di studio

**💡 Punti Chiave:**
Ogni legge si basa sulla precedente per creare una comprensione completa delle dinamiche del moto"""
            },
            "es": {
                "full": """Bienvenidos a la clase de Física de hoy sobre las Leyes del Movimiento de Newton.

Hoy vamos a explorar los principios fundamentales que gobiernan cómo los objetos se mueven e interactúan con las fuerzas. Empecemos con la Primera Ley de Newton, también conocida como la Ley de Inercia.

La Primera Ley de Newton establece que un objeto en reposo permanece en reposo, y un objeto en movimiento permanece en movimiento a velocidad constante, a menos que sea afectado por una fuerza externa. Esto puede parecer obvio, pero es realmente muy profundo cuando lo piensas.

Por ejemplo, si estás sentado en un carro y el carro se detiene repentinamente, tu cuerpo continúa moviéndose hacia adelante. Esto es porque tu cuerpo quiere mantener su estado de movimiento - eso es la inercia en acción.

Ahora, pasemos a la Segunda Ley de Newton, que es probablemente la más famosa: F igual ma. Fuerza igual masa por aceleración. Esta ley nos dice que la fuerza aplicada a un objeto es directamente proporcional a la masa del objeto y su aceleración.

Un ejemplo práctico: si empujas un carrito de compras con la misma fuerza, un carrito vacío acelerará mucho más rápido que un carrito lleno. Misma fuerza, diferente masa, diferente aceleración.

Finalmente, la Tercera Ley de Newton establece que para cada acción, hay una reacción igual y opuesta. Cuando caminas, empujas hacia atrás en el suelo, y el suelo empuja hacia adelante en ti.

Estas tres leyes forman la base de la mecánica clásica y nos ayudan a entender el movimiento en nuestro mundo cotidiano. La próxima clase exploraremos cómo estas leyes se aplican al movimiento circular y la gravedad.""",
                "summary": """📚 **Resumen de Clase de Física: Leyes del Movimiento de Newton**

**🎯 Conceptos Clave:**
• **Primera Ley de Newton (Ley de Inercia)**: Los objetos mantienen su estado de movimiento a menos que sean afectados por fuerzas externas
• **Segunda Ley de Newton**: F = ma (Fuerza = masa × aceleración)
• **Tercera Ley de Newton**: Cada acción tiene una reacción igual y opuesta

**💡 Puntos Principales:**
1. **Inercia explicada**: Los objetos resisten cambios en el movimiento - demostrado por el ejemplo del carro que se detiene
2. **Relación fuerza-masa**: Misma fuerza en diferentes masas produce diferentes aceleraciones (ejemplo del carrito de compras)
3. **Pares acción-reacción**: Caminar involucra empujar el suelo hacia atrás, el suelo empuja hacia adelante

**🔍 Ejemplos Prácticos:**
- Carro que se detiene → cuerpo continúa moviéndose hacia adelante (inercia)
- Carrito vacío vs lleno → diferentes aceleraciones con misma fuerza
- Caminar → pares de fuerzas acción-reacción

**📖 Vista Previa de Próxima Sesión:**
Aplicación de estas leyes al movimiento circular y fuerzas gravitacionales

**⭐ Enfoque de Estudio:**
Entender cómo estas tres leyes fundamentales explican los fenómenos de movimiento cotidianos""",
                "chapters": """📖 **Estructura de la Clase: Leyes del Movimiento de Newton**

**🎬 Introducción (0:00-2:30)**
- Resumen del curso y tema de hoy
- Importancia de las Leyes de Newton en la física

**📚 Capítulo 1: Primera Ley de Newton - Ley de Inercia (2:30-8:45)**
- Definición y explicación
- Ejemplos del mundo real (escenario del carro que se detiene)
- Entendimiento de la inercia en la vida diaria

**⚖️ Capítulo 2: Segunda Ley de Newton - F=ma (8:45-15:20)**
- Relación matemática entre fuerza, masa y aceleración
- Demostración práctica: ejemplo del carrito de compras
- Aplicaciones en resolución de problemas

**🔄 Capítulo 3: Tercera Ley de Newton - Acción-Reacción (15:20-22:10)**
- Principio de reacciones iguales y opuestas
- Caminar como ejemplo de pares acción-reacción
- Conceptos erróneos comunes abordados

**🎯 Conclusión y Próximos Pasos (22:10-25:00)**
- Resumen de las tres leyes
- Vista previa de la próxima clase: movimiento circular y gravedad
- Recomendaciones de estudio

**💡 Puntos Clave:**
Cada ley se basa en la anterior para crear un entendimiento completo de las dinámicas del movimiento"""
            },
            "fr": {
                "full": """Bienvenue au cours de Physique d'aujourd'hui sur les Lois du Mouvement de Newton.

Aujourd'hui, nous allons explorer les principes fondamentaux qui régissent comment les objets se déplacent et interagissent avec les forces. Commençons par la Première Loi de Newton, également connue sous le nom de Loi d'Inertie.

La Première Loi de Newton énonce qu'un objet au repos reste au repos, et un objet en mouvement reste en mouvement à vitesse constante, sauf s'il est soumis à une force externe. Cela peut sembler évident, mais c'est en fait très profond quand on y réfléchit.

Par exemple, si vous êtes assis dans une voiture et que la voiture s'arrête soudainement, votre corps continue de bouger vers l'avant. C'est parce que votre corps veut maintenir son état de mouvement - c'est l'inertie en action.

Maintenant, passons à la Deuxième Loi de Newton, qui est probablement la plus célèbre : F égale ma. Force égale masse fois accélération. Cette loi nous dit que la force appliquée à un objet est directement proportionnelle à la masse de l'objet et à son accélération.

Un exemple pratique : si vous poussez un chariot de courses avec la même force, un chariot vide accélérera beaucoup plus rapidement qu'un chariot plein. Même force, masse différente, accélération différente.

Enfin, la Troisième Loi de Newton énonce que pour chaque action, il y a une réaction égale et opposée. Quand vous marchez, vous poussez vers l'arrière sur le sol, et le sol pousse vers l'avant sur vous.

Ces trois lois forment la base de la mécanique classique et nous aident à comprendre le mouvement dans notre monde quotidien. Le prochain cours, nous explorerons comment ces lois s'appliquent au mouvement circulaire et à la gravité.""",
                "summary": """📚 **Résumé du Cours de Physique : Lois du Mouvement de Newton**

**🎯 Concepts Clés :**
• **Première Loi de Newton (Loi d'Inertie)** : Les objets maintiennent leur état de mouvement sauf s'ils sont soumis à des forces externes
• **Deuxième Loi de Newton** : F = ma (Force = masse × accélération)
• **Troisième Loi de Newton** : Chaque action a une réaction égale et opposée

**💡 Points Principaux :**
1. **Inertie expliquée** : Les objets résistent aux changements de mouvement - démontré par l'exemple de la voiture qui s'arrête
2. **Relation force-masse** : Même force sur différentes masses produit différentes accélérations (exemple du chariot de courses)
3. **Paires action-réaction** : Marcher implique pousser le sol vers l'arrière, le sol pousse vers l'avant

**🔍 Exemples Pratiques :**
- Voiture qui s'arrête → corps continue à bouger vers l'avant (inertie)
- Chariot vide vs plein → accélérations différentes avec même force
- Marcher → paires de forces action-réaction

**📖 Aperçu de la Prochaine Session :**
Application de ces lois au mouvement circulaire et aux forces gravitationnelles

**⭐ Focus d'Étude :**
Comprendre comment ces trois lois fondamentales expliquent les phénomènes de mouvement quotidiens""",
                "chapters": """📖 **Structure du Cours : Lois du Mouvement de Newton**

**🎬 Introduction (0:00-2:30)**
- Aperçu du cours et sujet d'aujourd'hui
- Importance des Lois de Newton en physique

**📚 Chapitre 1 : Première Loi de Newton - Loi d'Inertie (2:30-8:45)**
- Définition et explication
- Exemples du monde réel (scénario de la voiture qui s'arrête)
- Compréhension de l'inertie dans la vie quotidienne

**⚖️ Chapitre 2 : Deuxième Loi de Newton - F=ma (8:45-15:20)**
- Relation mathématique entre force, masse et accélération
- Démonstration pratique : exemple du chariot de courses
- Applications dans la résolution de problèmes

**🔄 Chapitre 3 : Troisième Loi de Newton - Action-Réaction (15:20-22:10)**
- Principe des réactions égales et opposées
- Marcher comme exemple de paires action-réaction
- Idées fausses communes abordées

**🎯 Conclusion et Prochaines Étapes (22:10-25:00)**
- Résumé des trois lois
- Aperçu du prochain cours : mouvement circulaire et gravité
- Recommandations d'étude

**💡 Points Clés :**
Chaque loi s'appuie sur la précédente pour créer une compréhension complète des dynamiques du mouvement"""
            },
            "de": {
                "full": """Willkommen zur heutigen Physikvorlesung über Newtons Bewegungsgesetze.

Heute werden wir die grundlegenden Prinzipien erforschen, die bestimmen, wie sich Objekte bewegen und mit Kräften interagieren. Beginnen wir mit Newtons Erstem Gesetz, auch bekannt als Trägheitsgesetz.

Newtons Erstes Gesetz besagt, dass ein Objekt in Ruhe in Ruhe bleibt, und ein Objekt in Bewegung in Bewegung bei konstanter Geschwindigkeit bleibt, es sei denn, es wird von einer äußeren Kraft beeinflusst. Das mag offensichtlich erscheinen, aber es ist tatsächlich sehr tiefgreifend, wenn man darüber nachdenkt.

Zum Beispiel, wenn Sie in einem Auto sitzen und das Auto plötzlich anhält, bewegt sich Ihr Körper weiter nach vorne. Das liegt daran, dass Ihr Körper seinen Bewegungszustand beibehalten möchte - das ist Trägheit in Aktion.

Nun gehen wir zu Newtons Zweitem Gesetz über, das wahrscheinlich das berühmteste ist: F gleich ma. Kraft gleich Masse mal Beschleunigung. Dieses Gesetz sagt uns, dass die auf ein Objekt angewendete Kraft direkt proportional zur Masse des Objekts und seiner Beschleunigung ist.

Ein praktisches Beispiel: Wenn Sie einen Einkaufswagen mit der gleichen Kraft schieben, wird ein leerer Wagen viel schneller beschleunigen als ein voller Wagen. Gleiche Kraft, verschiedene Masse, verschiedene Beschleunigung.

Schließlich besagt Newtons Drittes Gesetz, dass für jede Aktion eine gleiche und entgegengesetzte Reaktion existiert. Wenn Sie gehen, drücken Sie nach hinten auf den Boden, und der Boden drückt nach vorne auf Sie.

Diese drei Gesetze bilden die Grundlage der klassischen Mechanik und helfen uns, Bewegung in unserer alltäglichen Welt zu verstehen. In der nächsten Vorlesung werden wir erforschen, wie diese Gesetze auf Kreisbewegung und Schwerkraft angewendet werden.""",
                "summary": """📚 **Physikvorlesung Zusammenfassung: Newtons Bewegungsgesetze**

**🎯 Schlüsselkonzepte:**
• **Newtons Erstes Gesetz (Trägheitsgesetz)**: Objekte behalten ihren Bewegungszustand bei, es sei denn, sie werden von äußeren Kräften beeinflusst
• **Newtons Zweites Gesetz**: F = ma (Kraft = Masse × Beschleunigung)
• **Newtons Drittes Gesetz**: Jede Aktion hat eine gleiche und entgegengesetzte Reaktion

**💡 Hauptpunkte:**
1. **Trägheit erklärt**: Objekte widersetzen sich Änderungen in der Bewegung - demonstriert durch das Beispiel des anhaltenden Autos
2. **Kraft-Masse-Beziehung**: Gleiche Kraft auf verschiedene Massen erzeugt verschiedene Beschleunigungen (Einkaufswagen-Beispiel)
3. **Aktion-Reaktion-Paare**: Gehen beinhaltet das Drücken des Bodens nach hinten, Boden drückt nach vorne

**🔍 Praktische Beispiele:**
- Auto hält an → Körper bewegt sich weiter nach vorne (Trägheit)
- Leerer vs voller Einkaufswagen → verschiedene Beschleunigungen mit gleicher Kraft
- Gehen → Aktion-Reaktion-Kraftpaare

**📖 Vorschau auf nächste Sitzung:**
Anwendung dieser Gesetze auf Kreisbewegung und Gravitationskräfte

**⭐ Studienfokus:**
Verstehen, wie diese drei fundamentalen Gesetze alltägliche Bewegungsphänomene erklären""",
                "chapters": """📖 **Vorlesungsstruktur: Newtons Bewegungsgesetze**

**🎬 Einführung (0:00-2:30)**
- Kursüberblick und heutiges Thema
- Wichtigkeit von Newtons Gesetzen in der Physik

**📚 Kapitel 1: Newtons Erstes Gesetz - Trägheitsgesetz (2:30-8:45)**
- Definition und Erklärung
- Beispiele aus der realen Welt (Szenario des anhaltenden Autos)
- Verständnis von Trägheit im täglichen Leben

**⚖️ Kapitel 2: Newtons Zweites Gesetz - F=ma (8:45-15:20)**
- Mathematische Beziehung zwischen Kraft, Masse und Beschleunigung
- Praktische Demonstration: Einkaufswagen-Beispiel
- Anwendungen in der Problemlösung

**🔄 Kapitel 3: Newtons Drittes Gesetz - Aktion-Reaktion (15:20-22:10)**
- Prinzip gleicher und entgegengesetzter Reaktionen
- Gehen als Beispiel für Aktion-Reaktion-Paare
- Häufige Missverständnisse angesprochen

**🎯 Fazit und nächste Schritte (22:10-25:00)**
- Zusammenfassung der drei Gesetze
- Vorschau auf nächste Vorlesung: Kreisbewegung und Schwerkraft
- Studienempfehlungen

**💡 Wichtige Erkenntnisse:**
Jedes Gesetz baut auf dem vorherigen auf, um ein vollständiges Verständnis der Bewegungsdynamik zu schaffen"""
            }
        }
        
        # Get language-specific content or default to English
        content = language_content.get(language, language_content["en"])
        
        if processing_type == "full":
            transcript = content["full"]
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"transcript": transcript, "status": "completed"}}
            )
            
        elif processing_type == "summary":
            summary = content["summary"]
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"summary": summary, "status": "completed"}}
            )
            
        elif processing_type == "chapters":
            chapters = content["chapters"]
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"summary": chapters, "status": "completed"}}
            )
            
    except Exception as e:
        logging.error(f"Error in mock AI processing: {str(e)}")
        await db.recordings.update_one(
            {"id": recording_id},
            {"$set": {"status": "failed"}}
        )

# Auth Routes
@api_router.get("/auth/profile")
async def get_profile(x_session_id: str = Header(None)):
    """Get user profile from session ID"""
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Session ID required")
    
    # For demo, create a mock user
    user_data = {
        "id": str(uuid.uuid4()),
        "email": "demo@smartnotes.com",
        "name": "Demo User",
        "picture": "https://via.placeholder.com/150",
        "session_token": x_session_id
    }
    
    # Create or update user
    existing_user = await db.users.find_one({"email": user_data["email"]})
    if not existing_user:
        user = User(**user_data)
        await db.users.insert_one(user.dict())
    else:
        user = User(**existing_user)
    
    # Create session
    session = Session(
        user_id=user.id,
        session_token=x_session_id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    await db.sessions.insert_one(session.dict())
    
    return user_data

# Recording Routes
@api_router.post("/recordings", response_model=Recording)
async def create_recording(recording_data: RecordingCreate, current_user: User = Depends(get_current_user)):
    """Create a new recording"""
    recording = Recording(
        user_id=current_user.id,
        title=recording_data.title,
        audio_data=recording_data.audio_data,
        tags=recording_data.tags,
        notes=recording_data.notes,
        duration=recording_data.duration,
        status="uploaded"
    )
    
    await db.recordings.insert_one(recording.dict())
    return recording

@api_router.get("/recordings", response_model=List[Recording])
async def get_recordings(current_user: User = Depends(get_current_user)):
    """Get all recordings for the current user"""
    recordings = await db.recordings.find({"user_id": current_user.id}).sort("created_at", -1).to_list(100)
    return [Recording(**recording) for recording in recordings]

@api_router.get("/recordings/{recording_id}", response_model=Recording)
async def get_recording(recording_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific recording"""
    recording = await db.recordings.find_one({"id": recording_id, "user_id": current_user.id})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return Recording(**recording)

@api_router.post("/recordings/{recording_id}/process", response_model=ProcessingResponse)
async def process_recording(recording_id: str, request: TranscriptionRequest, current_user: User = Depends(get_current_user)):
    """Process recording for transcription/summarization"""
    recording = await db.recordings.find_one({"id": recording_id, "user_id": current_user.id})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # Update status to processing
    await db.recordings.update_one(
        {"id": recording_id},
        {"$set": {"status": "processing"}}
    )
    
    # Use user's preferred language or request language
    language = request.language if request.language else current_user.preferred_language
    
    # Process in background with language support
    asyncio.create_task(process_audio_with_ai(recording_id, recording["audio_data"], request.type, language))
    
    return ProcessingResponse(
        message=f"Processing started for {request.type} transcription in {language}",
        recording_id=recording_id,
        status="processing"
    )

@api_router.delete("/recordings/{recording_id}")
async def delete_recording(recording_id: str, current_user: User = Depends(get_current_user)):
    """Delete a recording"""
    result = await db.recordings.delete_one({"id": recording_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recording not found")
    return {"message": "Recording deleted successfully"}

@api_router.put("/recordings/{recording_id}")
async def update_recording(recording_id: str, update_data: dict, current_user: User = Depends(get_current_user)):
    """Update recording metadata"""
    recording = await db.recordings.find_one({"id": recording_id, "user_id": current_user.id})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # Only allow updating specific fields
    allowed_fields = {"title", "tags", "notes"}
    update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    if update_fields:
        await db.recordings.update_one(
            {"id": recording_id},
            {"$set": update_fields}
        )
    
    return {"message": "Recording updated successfully"}

# User Routes
@api_router.get("/user/profile", response_model=User)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@api_router.put("/user/language")
async def update_user_language(language_data: dict, current_user: User = Depends(get_current_user)):
    """Update user's preferred language"""
    supported_languages = ["en", "it", "es", "fr", "de"]
    new_language = language_data.get("language", "en")
    
    if new_language not in supported_languages:
        raise HTTPException(status_code=400, detail="Unsupported language")
    
    # Update user's preferred language
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"preferred_language": new_language}}
    )
    
    return {"message": f"Language updated to {new_language}", "language": new_language}

@api_router.get("/user/referral")
async def get_referral_info(current_user: User = Depends(get_current_user)):
    """Get referral code and discount info"""
    return {
        "referral_code": current_user.referral_code,
        "discount_amount": current_user.discount_amount,
        "monthly_cost": max(2.0 - current_user.discount_amount, 1.0)  # Minimum €1.00
    }

# Health check
@api_router.get("/")
async def root():
    return {"message": "SmartNotes API is running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()