"""
SentinelIQ MongoDB Connectivity & Health Management
Connects to MongoDB Atlas or local MongoDB using PyMongo.
Provides explicit connection lifecycle, timeouts, ping health checks, and honest error reporting.
"""
from typing import Tuple, Dict, Any, Optional
import pymongo
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from backend.app.config import settings

_mongo_client: Optional[pymongo.MongoClient] = None


def get_mongo_client() -> pymongo.MongoClient:
    """Get or initialize singleton PyMongo MongoClient."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = pymongo.MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=500,
            connectTimeoutMS=500,
            socketTimeoutMS=1000,
            appname="SentinelIQ"
        )
    return _mongo_client


def get_database():
    """Retrieve database instance from PyMongo client."""
    client = get_mongo_client()
    return client[settings.MONGODB_DATABASE]


def check_database_health() -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check MongoDB connectivity honestly.
    Never fabricates a successful connection if MongoDB is unreachable.
    Returns: (is_healthy, status_message, details_dict)
    """
    if settings.APP_STORAGE == "memory":
        return False, "Operating in isolated in-memory storage mode (mock / test).", {
            "database": "in_memory",
            "status": "memory_mode",
            "actionable_advice": "Configure MONGODB_URI in .env and set APP_STORAGE=mongodb to connect to live MongoDB Atlas."
        }

    try:
        client = get_mongo_client()
        # Explicit ping command to MongoDB server
        server_info = client.admin.command("ping")
        return True, "MongoDB connected and responsive.", {
            "database": settings.MONGODB_DATABASE,
            "status": "connected",
            "ping_result": server_info
        }
    except ServerSelectionTimeoutError as e:
        return False, "MongoDB connection timeout: Unable to reach MongoDB host.", {
            "error_type": "ServerSelectionTimeoutError",
            "uri": settings.MONGODB_URI.split("@")[-1] if "@" in settings.MONGODB_URI else settings.MONGODB_URI,
            "database": settings.MONGODB_DATABASE,
            "actionable_advice": "Check MONGODB_URI in .env. If using Atlas, ensure your current IP address is whitelisted in Network Access. If using local, start mongod service."
        }
    except PyMongoError as e:
        return False, f"MongoDB driver error: {str(e)}", {
            "error_type": type(e).__name__,
            "database": settings.MONGODB_DATABASE,
            "actionable_advice": "Verify database credentials, permissions, and network configuration."
        }
    except Exception as e:
        return False, f"Unexpected error connecting to database: {str(e)}", {
            "error_type": type(e).__name__,
            "database": settings.MONGODB_DATABASE,
            "actionable_advice": "Check system firewall, DNS resolution, and local network socket permissions."
        }


def close_mongo_connection():
    """Cleanly close PyMongo client."""
    global _mongo_client
    if _mongo_client is not None:
        try:
            _mongo_client.close()
        except Exception:
            pass
        _mongo_client = None
