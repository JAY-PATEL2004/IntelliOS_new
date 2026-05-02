"""
server.py - FastAPI server for IntelliOS log processing system
Provides endpoints for real-time log processing and topic matching
"""
import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import json
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'State_capturing_engine')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Restoration_engine')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Configure_browsers')))
from browser_capture import capture_browser_states
from app_capture import capture_app_states
from browser_restore import restore_browsers
from app_restore import restore_apps
from create_browser_shortcuts import create_browser_shortcuts

# Load environment variables
load_dotenv()

# Add parent directory to path to import IntelliOS modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import IntelliOS modules
from logging_config import setup_logging
from log_fetcher import fetch_windows_event_logs
from regex_parsers import parse_with_regex
from llm_layer import parse_with_llm
from vector_db import VectorDBManager
from topics import TOPICS
# Import the process_logs function from main.py
from main import process_logs


# Set up the logger
logger = logging.getLogger(__name__)
setup_logging()  # Use environment variable LOG_LEVEL

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

# Initialize vector database manager
vector_db = VectorDBManager()

# Define response models
class LogEntry(BaseModel):
    event_type: str
    summary: str
    app_name: Optional[str] = None
    file_path: Optional[str] = None
    status: Optional[str] = None
    operation_code: Optional[str] = None
    event_subtype: Optional[str] = None
    topic_matches: Optional[List[Dict[str, Any]]] = None

class LogResponse(BaseModel):
    logs: List[LogEntry]
    total_logs_processed: int
    regex_parsed: int
    llm_parsed: int
    failed_to_parse: int
    status: str

class TopicListResponse(BaseModel):
    topics: Dict[str, str]
    status: str


class RestoreResponse(BaseModel):
    status: str
    message: str
    details: Optional[Dict[str, bool]] = None


class CaptureResponse(BaseModel):
    status: str
    message: str
    saved_at: str
    file_path: str

# In-memory queue for background processed logs
processed_logs_queue = []
# Processing statistics
processing_stats = {
    "total_logs": 0,
    "regex_parsed": 0,
    "llm_parsed": 0,
    "failed_to_parse": 0
}

# Process logs in the background
def process_logs_background(channel: str, hours: int, limit: int, with_topics: bool):
    """Background task to process logs"""
    global processed_logs_queue
    global processing_stats
    
    # Calculate the start time for log fetching
    fetch_since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Use the process_logs function from main.py
    parsed_logs = process_logs(channel, fetch_since, limit)
    
    # Calculate statistics (this needs to be done separately since process_logs doesn't return these values)
    # In a production system, you'd want to modify process_logs to return these statistics
    total_logs = 0
    regex_parsed = 0
    llm_parsed = 0
    
    for provider, message in fetch_windows_event_logs(channel, fetch_since):
        total_logs += 1
        if limit is not None and total_logs > limit:
            break
            
        # Just count the logs to calculate stats, actual parsing is done by process_logs
        if parse_with_regex(provider, message) is not None:
            regex_parsed += 1
        elif parse_with_llm(provider, message) is not None:
            llm_parsed += 1
    
    # Store statistics
    processing_stats = {
        "total_logs": total_logs,
        "regex_parsed": regex_parsed,
        "llm_parsed": llm_parsed,
        "failed_to_parse": total_logs - regex_parsed - llm_parsed
    }
    
    # Match with topics if requested
    if with_topics and parsed_logs:
        enriched_logs = vector_db.add_logs(parsed_logs)
        # Store the enriched logs in the queue
        processed_logs_queue = enriched_logs
    else:
        # Store the regular logs in the queue
        processed_logs_queue = parsed_logs
    
    # Log processing summary
    logger.info(f"\nProcessing summary:")
    logger.info(f"Total logs processed: {total_logs}")
    if total_logs > 0:
        logger.info(f"Parsed with regex: {regex_parsed} ({regex_parsed/total_logs*100:.1f}%)")
        logger.info(f"Parsed with LLM: {llm_parsed} ({llm_parsed/total_logs*100:.1f}%)")
        logger.info(f"Failed to parse: {total_logs - regex_parsed - llm_parsed} ({(total_logs - regex_parsed - llm_parsed)/total_logs*100:.1f}%)")
        logger.info(f"Total successfully parsed: {len(parsed_logs)} ({len(parsed_logs)/total_logs*100:.1f}%)")

# Routes
@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint - health check"""
    return {"status": "online", "message": "IntelliOS API is running"}

@app.get("/api/topics", response_model=TopicListResponse, tags=["Topics"])
async def get_topics():
    """Get list of available topics with descriptions"""
    return {
        "topics": TOPICS,
        "status": "success"
    }

@app.post("/api/process-logs", response_model=LogResponse, tags=["Logs"])
async def process_logs_endpoint(
    background_tasks: BackgroundTasks,
    channel: str = Query("System", description="Windows Event Log channel to process"),
    hours: int = Query(1, description="Process logs from the last N hours"),
    limit: int = Query(10, description="Limit the number of logs to process"),
    with_topics: bool = Query(True, description="Match logs with topics")
):
    """
    Process logs in the background and return a job ID
    The actual log processing happens in the background
    """
    # Clear the queue
    global processed_logs_queue
    processed_logs_queue = []
    
    # Start background processing
    background_tasks.add_task(process_logs_background, channel, hours, limit, with_topics)
    
    return {
        "logs": [],
        "total_logs_processed": 0,
        "regex_parsed": 0,
        "llm_parsed": 0,
        "failed_to_parse": 0,
        "status": "processing_started"
    }

@app.get("/api/logs", response_model=LogResponse, tags=["Logs"])
async def get_logs():
    """Get the most recently processed logs"""
    global processed_logs_queue
    global processing_stats
    
    if not processed_logs_queue:
        return {
            "logs": [],
            "total_logs_processed": 0,
            "regex_parsed": 0,
            "llm_parsed": 0,
            "failed_to_parse": 0,
            "status": "no_logs_processed"
        }
    
    return {
        "logs": processed_logs_queue,
        "total_logs_processed": processing_stats["total_logs"],
        "regex_parsed": processing_stats["regex_parsed"],
        "llm_parsed": processing_stats["llm_parsed"],
        "failed_to_parse": processing_stats["failed_to_parse"],
        "status": "success"
    }

@app.get("/api/real-time-logs", tags=["Logs"])
async def get_real_time_logs(
    channel: str = Query("System", description="Windows Event Log channel to process"),
    hours: int = Query(1, description="Process logs from the last N hours"),
    limit: int = Query(5, description="Limit the number of logs to process"),
    with_topics: bool = Query(True, description="Match logs with topics")
):
    """
    Get real-time logs from Windows Event Log with topic matching
    This is a synchronous endpoint that processes logs and returns them immediately
    """
    # Calculate the start time for log fetching
    fetch_since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Process logs
    parsed_logs = process_logs(channel, fetch_since, limit)
    
    # Match with topics if requested
    if with_topics and parsed_logs:
        enriched_logs = vector_db.add_logs(parsed_logs)
        return {
            "logs": enriched_logs,
            "count": len(enriched_logs),
            "channel": channel,
            "hours": hours,
            "with_topics": with_topics,
            "status": "success"
        }
    else:
        return {
            "logs": parsed_logs,
            "count": len(parsed_logs),
            "channel": channel,
            "hours": hours,
            "with_topics": with_topics,
            "status": "success"
        }

@app.post("/api/query-logs", tags=["Logs"])
async def query_logs(
    query: str = Query(..., description="Query text to search for"),
    results: int = Query(5, description="Number of results to return")
):
    """Query the vector database for logs matching the query"""
    try:
        logs = vector_db.query_logs(query, results)
        return {
            "logs": logs,
            "count": len(logs),
            "query": query,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error querying logs: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying logs: {str(e)}")

@app.post("/api/clear-vector-db", tags=["Database"])
async def clear_vector_db():
    """Clear the vector database"""
    try:
        success = vector_db.clear_collection()
        if success:
            return {"status": "success", "message": "Vector database cleared successfully"}
        else:
            return {"status": "error", "message": "Failed to clear vector database"}
    except Exception as e:
        logger.error(f"Error clearing vector database: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing vector database: {str(e)}")

@app.get("/api/vector-db-stats", tags=["Database"])
async def get_vector_db_stats():
    """Get statistics about the vector database"""
    try:
        stats = vector_db.get_stats()
        return {
            "stats": stats,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting vector database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting vector database stats: {str(e)}")
    
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
@app.post("/api/capture", response_model=CaptureResponse, tags=["State Management"])
async def capture_state():
    """
    Capture current system state and save it to a file
    
    Args:
        request: CaptureRequest containing paths for state.json and browser_ports.json
        
    Returns:
        CaptureResponse with status and message
    """
    try:
        state_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..\\State\\state.json"))
        browser_ports_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..\\State\\browser_ports.json"))
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
            browsers = capture_browser_states(browser_ports_data)
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
            "saved_at": datetime.now().isoformat(),
            "user": os.environ.get("USERNAME", ""),
            "browsers": browsers,
            "apps": apps
        }
        
        # Save state to file
        with open(state_file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            
        return CaptureResponse(
            status="success",
            message="State captured successfully",
            saved_at=state["saved_at"],
            file_path=state_file_path
        )
            
    except Exception as e:
        logger.error(f"Error capturing state: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error capturing state: {str(e)}"
        )

@app.post("/api/restore", response_model=RestoreResponse, tags=["State Management"])
async def restore_state():
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
        state_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..\\State\\state.json"))

        if not os.path.exists(state_file_path):
            raise HTTPException(
                status_code=404,
                detail=f"State file not found: {state_file_path}"
            )

        # Read state file
        state = {}
        try:
            with open(state_file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except Exception as e:
            logger.error(f"Error reading state file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error reading state file: {str(e)}"
            )

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

if __name__ == "__main__":
    # Run the server
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
