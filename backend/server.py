"""
server.py - FastAPI server for IntelliOS log processing system
Provides endpoints for real-time log processing and topic matching
"""
import os
import sys
import numpy as np
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import json
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from sentence_transformers import SentenceTransformer

# Initialize Firebase
from firebase_admin import credentials, firestore, initialize_app, get_app, App

# Initialize Firebase safely (avoid re-initialization)
try:
    app_ = get_app()
except ValueError:
    cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), "FireBase", "serviceAccountKey.json"))
    app_ = initialize_app(cred)

db = firestore.client(app_)

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'State_capturing_engine')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Restoration_engine')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Configure_browsers')))
# from browser_capture import capture_browser_states
# from app_capture import capture_app_states
# from browser_restore import restore_browsers
# from app_restore import restore_apps
# from create_browser_shortcuts import create_browser_shortcuts

# Load environment variables
load_dotenv()

# Add parent directory to path to import IntelliOS modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from logging_config import setup_logging

# Set up the logger
logger = logging.getLogger(__name__)
# setup_logging()  # Use environment variable LOG_LEVEL


# Initialize FastAPI app
app = FastAPI(
    title="IntelliOS API",
    description="API for IntelliOS Log Processing System",
    version="1.0.0",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LAST_CAPTURED = os.environ.get('LAST_CAPTURED')
if LAST_CAPTURED is None:
    LAST_CAPTURED = datetime.fromtimestamp(0, tz=timezone(timedelta(hours=5, minutes=30))).isoformat()


# Define response models


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    message: str
    workspaces: Optional[Dict[str, Dict[str, Any]]] = None

class SignupRequest(BaseModel):
    username: str
    password: str
    email: str
    name: str

class SignupResponse(BaseModel):
    status: str
    message: str

class CaptureResponse(BaseModel):
    status: str
    message: str
    state: Optional[Dict[str, Any]] = None

class RestoreRequest(BaseModel):
    state: Optional[Dict[str, Any]] = None

class RestoreResponse(BaseModel):
    status: str
    message: str
    details: Optional[Dict[str, bool]] = None

class CreateWorkspaceRequest(BaseModel):
    username: str
    workspace_name: str
    state: Dict[str, Any]

class CreateWorkspaceResponse(BaseModel):
    status: str
    message: str

class GetWorkspacesRequest(BaseModel):
    username: str

class GetWorkspacesResponse(BaseModel):
    status: str
    workspaces: Dict[str, Dict[str, Any]]

class DeleteWorkspaceRequest(BaseModel):
    username: str
    workspace_name: str

class DeleteWorkspaceResponse(BaseModel):
    status: str
    message: str

class SuggestionsRequest(BaseModel):
    state: Dict[str, Any]

class SuggestionsResponse(BaseModel):
    status: str
    topics: Any

# Routes
@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint - health check"""
    return {"status": "online", "message": "IntelliOS API is running"}

@app.post("/api/login", response_model=LoginResponse, tags=["Authentication"])
async def login(request: LoginRequest):
    """
    Authenticate user login
    """
    try:
        # Get user document from Firestore
        doc = db.collection("DDNA").document(request.username).get()
        
        if not doc.exists:
            return LoginResponse(
                status="error",
                message="Username not found",
                workspaces=None
            )
            
        user_data = doc.to_dict()
        if user_data.get("password") != request.password:
            return LoginResponse(
                status="error",
                message="Incorrect Password",
                workspaces=None
            )
            
        # Return success with workspaces
        return LoginResponse(
            status="success",
            message="Successful",
            workspaces=user_data.get("workspaces", {})
        )
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

@app.post("/api/signup", response_model=SignupResponse, tags=["Authentication"])
async def signup(request: SignupRequest):
    """
    Create new user account
    """
    try:
        # Check if username already exists
        doc = db.collection("DDNA").document(request.username).get()
        if doc.exists:
            return SignupResponse(
                status="error",
                message="Username already exists"
            )
            
        # Create new user document
        user_data = {
            "username": request.username,
            "password": request.password,
            "email": request.email,
            "name": request.name,
            "workspaces": {}
        }
        
        db.collection("DDNA").document(request.username).set(user_data)
        
        return SignupResponse(
            status="success",
            message="Account created successfully"
        )
            
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Signup failed: {str(e)}"
        )

@app.post("/api/workspace", response_model=CreateWorkspaceResponse, tags=["Workspace Management"])
async def create_update_workspace(request: CreateWorkspaceRequest):
    """
    Create or update a workspace with the given name and state
    
    Args:
        request: CreateWorkspaceRequest containing username, workspace_name and state
        
    Returns:
        CreateWorkspaceResponse with status and message
    """
    try:
        # Get user document
        doc_ref = db.collection("DDNA").document(request.username)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        # Get current workspaces
        user_data = doc.to_dict()
        workspaces = user_data.get("workspaces", {})
        
        # Add or update workspace
        workspaces[request.workspace_name] = request.state
        
        # Update Firestore document
        doc_ref.update({
            "workspaces": workspaces
        })
            
        return CreateWorkspaceResponse(
            status="success",
            message=f"Workspace '{request.workspace_name}' created/updated successfully"
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating workspace: {str(e)}"
        )

@app.post("/api/workspaces", response_model=GetWorkspacesResponse, tags=["Workspace Management"])
async def get_all_workspaces(request: GetWorkspacesRequest):
    """
    Get all workspaces and their states for a user
    
    Args:
        request: GetWorkspacesRequest containing username
        
    Returns:
        GetWorkspacesResponse containing a dictionary of workspace names and their states
    """
    try:
        # Get user document
        doc = db.collection("DDNA").document(request.username).get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        user_data = doc.to_dict()
        workspaces = user_data.get("workspaces", {})
                    
        return GetWorkspacesResponse(
            status="success",
            workspaces=workspaces
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting workspaces: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting workspaces: {str(e)}"
        )

@app.delete("/api/workspace", response_model=DeleteWorkspaceResponse, tags=["Workspace Management"])
async def delete_workspace(request: DeleteWorkspaceRequest):
    """
    Delete a workspace for a user
    
    Args:
        request: DeleteWorkspaceRequest containing username and workspace_name
        
    Returns:
        DeleteWorkspaceResponse with status and message
    """
    try:
        # Get user document
        doc_ref = db.collection("DDNA").document(request.username)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        # Get current workspaces
        user_data = doc.to_dict()
        workspaces = user_data.get("workspaces", {})
        
        # Check if workspace exists
        if request.workspace_name not in workspaces:
            raise HTTPException(
                status_code=404,
                detail=f"Workspace '{request.workspace_name}' not found"
            )
            
        # Delete workspace
        del workspaces[request.workspace_name]
        
        # Update Firestore document
        doc_ref.update({
            "workspaces": workspaces
        })
        
        return DeleteWorkspaceResponse(
            status="success",
            message=f"Workspace '{request.workspace_name}' deleted successfully"
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting workspace: {str(e)}"
        )
    
@app.get("/api/create_shortcuts")
async def create_shortcuts():
    try:
        create_browser_shortcuts()
        return {
            "status": "success",
            "message": "Shortcuts successfully created"
        }
    except Exception as e:
        logger.error(f"Error creating shortcuts : {e}")
        raise HTTPException(status_code=500, detail=f"Error creating shortcuts : {str(e)}")

# State Restoration endpoints
@app.get("/api/capture", response_model=CaptureResponse, tags=["State Management"])
async def capture_state():
    """
    Capture current system state and save it to a file
    
    Args:
        request: CaptureRequest containing paths for state.json and browser_ports.json
        
    Returns:
        CaptureResponse with status and message
    """
    try:
        state_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "State\\state.json"))
        browser_ports_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "State\\browser_ports.json"))
        # Ensure output directory exists
        os.makedirs(os.path.dirname(state_file_path), exist_ok=True)

        if not os.path.exists(browser_ports_file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Browser ports file not found: {browser_ports_file_path}"
            )
        
        # Read browser ports file
        browser_ports_data = {}
        try:
            with open(browser_ports_file_path, 'r', encoding='utf-8') as f:
                browser_ports_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading browser ports file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error reading browser ports file: {str(e)}"
            )

        browsers = []
        apps = []
        #Capture browser states
        try:
            browsers = capture_browser_states(browser_ports_data, LAST_CAPTURED)
        except Exception as e:
            logger.error(f"Error capturing browser states: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error capturing browser states: {str(e)}"
            )
        # Capture app states
        try:
            apps = capture_app_states()
        except Exception as e:
            logger.error(f"Error capturing app states: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error capturing app states: {str(e)}"
            )
        
        # Create state object
        state = {
            "saved_at": datetime.now(tz=timezone(timedelta(hours=5, minutes=30))).isoformat(),
            "user": os.environ.get("USERNAME", ""),
            "browsers": browsers,
            "apps": apps
        }
        env_file = os.path.join(os.getcwd(), ".env")
        env_vars = {}
        ist_now = datetime.now(tz=timezone(timedelta(hours=5, minutes=30))).isoformat()
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        key, val = line.strip().split("=", 1)
                        env_vars[key] = val
        env_vars["LAST_CAPTURED"] = ist_now
        with open(env_file, "w") as f:
            for k, v in env_vars.items():
                f.write(f"{k}={v}\n")
        print(f"[SUCCESS] Environment file updated with LAST_CAPTURED={ist_now}")
        # os.environ.update({"LAST_CAPTURED":datetime.now(tz=timezone(timedelta(hours=5, minutes=30))).isoformat()})
        
        # Save state to file
        with open(state_file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

            
        return CaptureResponse(
            status="success",
            message="State captured successfully",
            state=state
        )
            
    except Exception as e:
        logger.error(f"Error capturing state: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error capturing state: {str(e)}"
        )

@app.post("/api/restore", response_model=RestoreResponse, tags=["State Management"], )
async def restore_state(request:dict):
    """
    Restore system state from a state file
    
    Args:
        request: RestoreRequest containing the path to the state file
        
    Returns:
        RestoreResponse with status and message
        
    Raises:
        HTTPException: If there are any errors during the restoration process
    """
    try:
        # state_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..\\State\\state.json"))

        # if not os.path.exists(state_file_path):
        #     raise HTTPException(
        #         status_code=404,
        #         detail=f"State file not found: {state_file_path}"
        #     )

        # # Read state file
        # state = {}
        # try:
        #     with open(state_file_path, 'r', encoding='utf-8') as f:
        #         state = json.load(f)
        # except Exception as e:
        #     logger.error(f"Error reading state file: {e}")
        #     raise HTTPException(
        #         status_code=500,
        #         detail=f"Error reading state file: {str(e)}"
        #     )

        state = request
        print(state)

        restoration_details = {
            "browsers_restored": False,
            "apps_restored": False
        }

        

        # Restore browsers
        try:
            restore_browsers(state)
            restoration_details["browsers_restored"] = True
        except Exception as e:
            logger.error(f"Error restoring browsers: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error restoring browsers: {str(e)}"
            )

        # Restore apps
        try:
            restore_apps(state)
            restoration_details["apps_restored"] = True
        except Exception as e:
            logger.error(f"Error restoring apps: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error restoring apps: {str(e)}"
            )

        return RestoreResponse(
            status="success",
            message="State restored successfully",
            details=restoration_details
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in restore_state: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.post("/api/suggestions", response_model=SuggestionsResponse, tags=["Workspace Suggestions"])
async def create_update_workspace(request: SuggestionsRequest):
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')

        def extract_context(data):
            tabs = []
            apps = []
            files = []

            # Extract browser data
            for browser in data.get("browsers", []):
                for window in browser.get("windows", []):
                    for tab in window.get("tabs", []):
                        tabs.append(tab["title"])

            # Extract app usage
            for app in data.get("apps", []):
                apps.append(app["name"])
                for item in app.get("items", []):
                    files.append(item)

            context = f"""
            Websites visited: {', '.join(tabs)}
            Applications used: {', '.join(apps)}
            Files accessed: {', '.join(files)}
            """

            return context

        topics = {
            # Work & Productivity
            "work_productivity": "office work productivity tasks reports spreadsheets documents meetings professional efficiency time management",
            "project_management": "planning projects tracking tasks deadlines agile scrum kanban jira teamwork coordination execution",
            "communication_professional": "emails messaging slack teams zoom calls professional communication collaboration discussion",
            "documentation": "writing documentation reports manuals notes technical writing knowledge base confluence notion",
            "time_management": "planning schedule calendar reminders organizing tasks productivity improvement daily planning",

            # Technology & Development
            "programming": "software development coding debugging writing code programming languages development environment",
            "web_development": "building websites web apps frontend backend html css javascript APIs servers",
            "mobile_development": "android ios app development mobile applications react native flutter coding",
            "machine_learning": "artificial intelligence machine learning data science model training neural networks datasets",
            "data_analytics": "data analysis visualization excel tableau power bi dashboards insights statistics",
            "cybersecurity": "security hacking encryption network security vulnerabilities penetration testing privacy",
            "devops_cloud": "cloud computing docker kubernetes CI CD deployment AWS Azure infrastructure servers",
            "database_management": "databases SQL queries data storage management relational databases mongodb",
            "software_testing": "testing software QA debugging test cases automation testing quality assurance",
            "system_design": "system architecture scalability design patterns backend systems distributed systems",

            # Learning & Education
            "learning_general": "studying education tutorials courses online learning research reading knowledge",
            "academic_study": "school college subjects lectures assignments exams textbooks notes",
            "skill_development": "learning new skills self improvement upskilling training practice growth",
            "certifications": "preparing exams certifications online courses credentials professional learning",
            "research_work": "reading research papers academic journals technical documents analysis",

            # Entertainment & Leisure
            "video_entertainment": "watching videos youtube netflix movies shows streaming entertainment",
            "music_audio": "listening music songs spotify podcasts audio entertainment relaxation",
            "gaming": "playing video games online multiplayer gaming entertainment competition",
            "social_media": "scrolling instagram facebook twitter memes reels content consumption",
            "live_streaming": "watching live streams twitch youtube live gaming streaming interaction",

            # Internet Usage
            "web_browsing": "general internet browsing random searches reading articles casual surfing",
            "news_consumption": "reading news current affairs politics world updates journalism media",
            "online_shopping": "ecommerce browsing products amazon flipkart purchasing comparing prices",
            "blog_reading": "reading blogs articles medium informational content knowledge sharing",

            # Social & Communication
            "personal_communication": "chatting messaging whatsapp friends family casual conversations social interaction",
            "professional_networking": "linkedin networking career connections professional discussions job networking",
            "community_engagement": "forums reddit quora discussions group participation community interaction",
            "email_management": "checking emails inbox replying organizing communication email usage",

            # Creativity & Design
            "graphic_design": "designing graphics photoshop illustrator visual content creativity",
            "ui_ux_design": "user interface design user experience prototyping figma adobe xd wireframes",
            "video_editing": "editing videos premiere pro after effects filmmaking content creation",
            "animation": "creating animations motion graphics 2D 3D animation creative work",
            "creative_writing": "writing stories blogs storytelling content creation articles",

            # Career & Finance
            "job_search": "searching jobs applying resumes interviews hiring opportunities",
            "career_planning": "career growth planning goals professional development future planning",
            "finance_management": "budgeting expenses savings personal finance banking money management",
            "stock_trading": "stock market trading investing crypto financial markets analysis",
            "freelancing": "freelance work gigs remote work clients projects independent work",

            # Health & Lifestyle
            "health_fitness": "exercise workouts gym yoga fitness health improvement physical activity",
            "mental_wellbeing": "meditation mindfulness stress relief relaxation mental health self care",
            "nutrition": "diet healthy eating food nutrition meal planning health",
            "sleep_management": "sleep tracking routines rest recovery health habits",

            # Daily Life
            "daily_planning": "planning day routine tasks reminders organizing personal life",
            "note_taking": "writing notes jotting ideas reminders digital notes organization",
            "file_management": "organizing files folders documents storage data handling",
            "task_management": "tracking tasks todo lists productivity tools organization",

            # Utilities & Tools
            "system_utilities": "system tools settings file explorer internet speed test utilities",
            "productivity_tools": "using excel notion calendar reminders tools task managers",
            "automation_tools": "automation scripts workflows efficiency tools repetitive task automation",

            # Travel & Real World
            "travel_planning": "planning trips booking hotels flights itineraries travel research",
            "navigation_maps": "using maps directions gps location travel navigation",
            "local_services": "searching nearby services restaurants shops local businesses",

            # Food & Cooking
            "cooking": "recipes cooking food preparation kitchen meals home cooking",
            "food_ordering": "ordering food online zomato swiggy delivery restaurants",
            "restaurant_exploration": "exploring restaurants cafes food places dining reviews",

            # Shopping & Lifestyle
            "fashion": "clothing fashion trends outfits shopping style accessories",
            "beauty_care": "skincare makeup grooming beauty products self care",
            "home_improvement": "home decor furniture interior design maintenance",

            # Education Specific
            "exam_preparation": "studying for exams competitive exams practice tests revision",
            "online_courses": "taking online courses udemy coursera learning platforms",
            "group_study": "studying with peers discussions collaborative learning",

            # Technical Deep Work
            "problem_solving": "logical reasoning puzzles coding challenges analytical thinking",
            "algorithm_practice": "data structures algorithms coding practice leetcode competitive programming",
            "debugging": "fixing bugs troubleshooting errors debugging code issues",

            # Content Creation
            "content_creation": "creating digital content videos blogs social media posts",
            "blogging": "writing blogs publishing articles content platforms",
            "podcasting": "recording podcasts audio content speaking broadcasting",

            # Media Consumption
            "sports_watching": "watching sports cricket football matches live highlights",
            "movie_browsing": "searching movies reviews trailers film exploration",
            "celebrity_following": "following celebrities news entertainment gossip media",

            # Personal Growth
            "self_improvement": "personal growth habits motivation productivity improvement mindset",
            "goal_setting": "setting goals planning achievements tracking progress",
            "journaling": "writing journal reflections personal thoughts diary",

            # Misc Digital Activities
            "file_downloading": "downloading files media software internet downloads",
            "software_installation": "installing applications programs setup configuration",
            "system_monitoring": "checking system performance cpu memory usage monitoring",

            # Collaboration & Work
            "team_collaboration": "working in teams shared documents group projects collaboration tools",
            "meeting_management": "attending meetings scheduling calls discussions zoom google meet",

            # Advanced Tech
            "blockchain_crypto": "blockchain cryptocurrency bitcoin ethereum web3 decentralized systems",
            "iot_embedded": "iot devices embedded systems sensors microcontrollers hardware programming",
            "robotics": "robotics automation machines control systems engineering",

            # Miscellaneous
            "event_planning": "organizing events functions scheduling arrangements coordination",
            "volunteering": "community service helping others social work volunteering",
            "gaming_streaming": "streaming gameplay content creation gaming audience interaction",
            "memes_browsing": "browsing memes humor entertainment casual fun",
            "random_exploration": "exploring random topics curiosity internet wandering discovery"
        }

        context_text = extract_context(request.state)

        context_embedding = model.encode(context_text)

        topic_embeddings = {
            topic: model.encode(description)
            for topic, description in topics.items()
        }

        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        scores = {}

        for topic, emb in topic_embeddings.items():
            sim = cosine_similarity(context_embedding, emb)
            scores[topic] = max(sim, 0)  # remove negative values
        
        scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10])

        total = sum(scores.values())

        percentages = {
            topic: round((score / total) * 100, 2)
            for topic, score in scores.items()
        }
            
        return SuggestionsResponse(
            status="success",
            topics=[{"topic": topic, "percentage": round((score / total) * 100, 2)} for topic, score in scores.items()]
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error loading suggestions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading suggestions: {str(e)}"
        )

if __name__ == "__main__":
    # Run the server
    # Note: reload=True watches the project files and restarts the process on any
    # file change. Many components write files under the repository (for
    # example state.json, logs, or vector DB files) which can trigger an
    # endless restart loop. For development use the CLI with --reload when
    # needed; here we disable reload to avoid watch-induced restart storms.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False)
