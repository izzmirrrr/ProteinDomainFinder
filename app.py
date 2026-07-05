import binascii
import hashlib
import hmac
import logging
import re
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Dict, List, Optional, Tuple

from bson import ObjectId
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from pymongo import DESCENDING, ReturnDocument, UpdateOne

from analysis import ProteinAnalyzer
from config import settings
from database import (
    history_collection as predictions_collection,
    password_resets_collection,
    popular_collection,
    proteins_collection,
    users_collection,
)
from fasta_parser import FASTAParser
from import_data import import_fasta_files, prepare_protein_doc
from rules_engine import DomainRulesEngine
from utils import ProteinMatcher

# ---------- JWT & HASHING ----------
import os
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-render")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
PASSWORD_RESET_EXPIRE_MINUTES = 10
PASSWORD_RESET_CODE_DIGITS = 6
PASSWORD_RESET_MAX_ATTEMPTS = 5

analyzer = ProteinAnalyzer()
matcher = ProteinMatcher()
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${binascii.hexlify(pwdhash).decode('utf-8')}"


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed or "$" not in hashed:
        return False
    salt, stored = hashed.split("$", 1)
    pwdhash = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hmac.compare_digest(binascii.hexlify(pwdhash).decode("utf-8"), stored)


def validate_password(password: str) -> bool:
    return len(password) >= 8 and bool(re.search(r"\d", password)) and bool(re.search(r"[A-Za-z]", password))


def normalize_email(email: str) -> str:
    return email.strip().lower()


def find_user_by_email(email: str) -> Optional[Dict]:
    normalized = normalize_email(email)
    return users_collection.find_one({"email": normalized}) or users_collection.find_one(
        {"email": {"$regex": f"^{re.escape(normalized)}$", "$options": "i"}}
    )


def normalize_reset_code(code: str) -> str:
    return re.sub(r"\D", "", code or "")


def hash_reset_code(user_id: str, code: str) -> str:
    message = f"{user_id}:{normalize_reset_code(code)}".encode("utf-8")
    return hmac.new(JWT_SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()


def password_reset_email_enabled() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)


def password_reset_available() -> bool:
    return True


def send_password_reset_email(email: str, reset_code: str) -> None:
    """Send password reset email via SMTP. Raises exception if SMTP not configured or fails."""
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        raise ValueError("SMTP credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD in .env file.")
    
    message = EmailMessage()
    message["Subject"] = "Your Protein Domain Finder reset code"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    message.set_content(
        "Use this one-time code to reset your Protein Domain Finder password:\n\n"
        f"{reset_code}\n\n"
        f"This code expires in {PASSWORD_RESET_EXPIRE_MINUTES} minutes and can only be used once.\n\n"
        "If you did not request this reset, you can ignore this email."
    )
    message.add_alternative(
        f"""
        <html>
          <body>
            <p>Use this one-time code to reset your Protein Domain Finder password:</p>
            <p style="font-size: 24px; font-weight: 700; letter-spacing: 4px;">{reset_code}</p>
            <p>This code expires in {PASSWORD_RESET_EXPIRE_MINUTES} minutes and can only be used once.</p>
            <p>If you did not request this reset, you can ignore this email.</p>
          </body>
        </html>
        """,
        subtype="html",
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info(f"Password reset email sent successfully to {email}")
    except smtplib.SMTPAuthenticationError:
        logger.error(f"SMTP Authentication failed for {settings.SMTP_USERNAME}. Check your Gmail app password.")
        raise ValueError(f"SMTP authentication failed. Verify your Gmail credentials and app password at https://myaccount.google.com/apppasswords")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email to {email}: {str(e)}")
        raise ValueError(f"SMTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error sending email to {email}: {str(e)}")
        raise ValueError(f"Could not send email: {str(e)}")


def log_password_reset_code(email: str, reset_code: str) -> None:
    logger.warning("Password reset code for %s: %s", email, reset_code)


def create_password_reset_code(user: Dict) -> Tuple[str, datetime]:
    now = datetime.utcnow()
    password_resets_collection.update_many(
        {
            "user_id": user["user_id"],
            "used_at": {"$exists": False},
            "expires_at": {"$gt": now},
        },
        {"$set": {"used_at": now, "invalidated_at": now}},
    )

    reset_code = f"{secrets.randbelow(10 ** PASSWORD_RESET_CODE_DIGITS):0{PASSWORD_RESET_CODE_DIGITS}d}"
    expires_at = now + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)
    password_resets_collection.insert_one(
        {
            "user_id": user["user_id"],
            "email": user["email"],
            "code_hash": hash_reset_code(user["user_id"], reset_code),
            "created_at": now,
            "expires_at": expires_at,
            "attempts": 0,
            "delivery": "smtp" if password_reset_email_enabled() else "code",
        }
    )
    return reset_code, expires_at


def find_latest_password_reset(user_id: str) -> Optional[Dict]:
    return password_resets_collection.find_one(
        {
            "user_id": user_id,
            "expires_at": {"$gt": datetime.utcnow()},
            "used_at": {"$exists": False},
            "attempts": {"$lt": PASSWORD_RESET_MAX_ATTEMPTS},
        },
        sort=[("created_at", DESCENDING)],
    )


def find_matching_password_reset(
    email: str,
    code: str,
    record_failure: bool = True,
) -> Tuple[Optional[Dict], Optional[Dict]]:
    user = find_user_by_email(email)
    if not user:
        return None, None

    reset_doc = find_latest_password_reset(user["user_id"])
    if not reset_doc:
        return user, None

    reset_code = normalize_reset_code(code)
    expected_hash = reset_doc.get("code_hash", "")
    candidate_hash = hash_reset_code(user["user_id"], reset_code)
    code_matches = (
        len(reset_code) == PASSWORD_RESET_CODE_DIGITS
        and hmac.compare_digest(candidate_hash, expected_hash)
    )
    if not code_matches:
        if record_failure:
            password_resets_collection.update_one(
                {"_id": reset_doc["_id"], "used_at": {"$exists": False}},
                {"$inc": {"attempts": 1}, "$set": {"last_attempt_at": datetime.utcnow()}},
            )
        return user, None

    return user, reset_doc


def consume_password_reset_code(email: str, code: str) -> Tuple[Optional[Dict], Optional[Dict]]:
    user, reset_doc = find_matching_password_reset(email, code)
    if not user or not reset_doc:
        return user, None

    now = datetime.utcnow()
    consumed_doc = password_resets_collection.find_one_and_update(
        {
            "_id": reset_doc["_id"],
            "expires_at": {"$gt": now},
            "used_at": {"$exists": False},
            "attempts": {"$lt": PASSWORD_RESET_MAX_ATTEMPTS},
        },
        {"$set": {"used_at": now}},
        return_document=ReturnDocument.BEFORE,
    )
    if consumed_doc:
        password_resets_collection.update_many(
            {
                "user_id": consumed_doc["user_id"],
                "_id": {"$ne": consumed_doc["_id"]},
                "used_at": {"$exists": False},
            },
            {"$set": {"used_at": now, "invalidated_at": now}},
        )
    return user, consumed_doc


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub"), payload.get("email")
    except JWTError:
        return None, None


def auth_user_id(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    user_id, _ = verify_token(authorization[7:])
    return user_id


def public_user_doc(user: Dict) -> Dict:
    clean = jsonable_doc({key: value for key, value in user.items() if key != "password_hash"})
    clean["role"] = clean.get("role", "user")
    clean["is_active"] = clean.get("is_active", True)
    return clean


def current_user(authorization: Optional[str]) -> Dict:
    user_id = auth_user_id(authorization)
    if not user_id:
        raise HTTPException(401, "Authentication required")
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    if user.get("is_active", True) is False:
        raise HTTPException(403, "Account is disabled")
    return user


def require_admin(authorization: Optional[str]) -> Dict:
    user = current_user(authorization)
    if user.get("role", "user") != "admin":
        raise HTTPException(403, "Admin access required")
    return user


def jsonable_doc(doc: Dict) -> Dict:
    clean = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            clean[key] = str(value)
        elif isinstance(value, datetime):
            clean[key] = value.isoformat()
        else:
            clean[key] = value
    return clean


def query_hash(query: str) -> str:
    normalized = " ".join(query.strip().upper().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def protein_response(doc: Dict) -> Dict:
    domain = doc.get("domain") or "Sequence Characterized"
    domain_family = doc.get("domain_family") or domain
    function = doc.get("function") or "Protein information is derived from the imported FASTA record and sequence analysis."
    return {
        "id": str(doc.get("_id", "")),
        "protein_id": doc.get("protein_id", ""),
        "protein_name": doc.get("protein_name", ""),
        "sequence": doc.get("sequence", ""),
        "domain": domain,
        "domain_family": domain_family,
        "function": function,
        "organism": doc.get("organism", "Unknown"),
        "length": doc.get("length", 0),
    }


def find_dataset_matches(validation: Dict, query: str) -> List[Dict]:
    clean_value = validation.get("clean_value", query).strip()
    query_type = validation.get("type")

    if query_type == "uniprot_id":
        cursor = proteins_collection.find({"protein_id": clean_value.upper()}).limit(5)
    elif query_type in {"sequence", "fasta_single"}:
        clean_seq = analyzer.clean_sequence(clean_value)
        if len(clean_seq) < 10:
            return []
        cursor = proteins_collection.find({"sequence": {"$regex": re.escape(clean_seq)}}).limit(5)
    elif clean_value:
        cursor = proteins_collection.find(
            {"$text": {"$search": clean_value}},
            {"score": {"$meta": "textScore"}},
        ).sort([("score", {"$meta": "textScore"})]).limit(5)
    else:
        return []

    return [protein_response(doc) for doc in cursor]


def build_prediction_result(query: str) -> Dict:
    if not query or not query.strip():
        raise HTTPException(400, "It's not a protein sequence. Please enter a valid amino-acid sequence, FASTA record, or UniProt ID from the dataset.")

    validation = matcher.validate_and_clean_input(query)
    warnings = validation.get("warnings", [])
    if validation.get("type") == "protein_name" and len(query.strip().split()) > 1:
        raise HTTPException(400, "It's not a protein sequence. Use only the standard amino-acid letters ACDEFGHIKLMNPQRSTVWY, or search a UniProt ID already imported into the database.")
    if not validation.get("is_valid") and len(query.strip().split()) > 1:
        raise HTTPException(400, "It's not a protein sequence. Use only the standard amino-acid letters ACDEFGHIKLMNPQRSTVWY, or search a UniProt ID already imported into the database.")

    dataset_matches = find_dataset_matches(validation, query)

    if not validation.get("is_valid") and not dataset_matches:
        raise HTTPException(400, "It's not a protein sequence. Use only the standard amino-acid letters ACDEFGHIKLMNPQRSTVWY, or search a UniProt ID already imported into the database.")

    sequence = validation.get("clean_value", "")
    if validation.get("type") == "uniprot_id":
        protein = proteins_collection.find_one({"protein_id": sequence})
        if protein:
            sequence = protein.get("sequence", "")
        else:
            warnings.append("No matching protein ID was found in the imported dataset.")

    if validation.get("type") == "fasta_multiple":
        first = validation.get("parsed_fasta", [{}])[0]
        sequence = first.get("sequence", "")
        warnings.append("Multiple FASTA records were supplied; prediction uses the first sequence.")

    if not sequence and dataset_matches:
        sequence = dataset_matches[0].get("sequence", "")
    sequence = analyzer.clean_sequence(sequence)
    if not sequence:
        raise HTTPException(400, "It's not a protein sequence. The app could not extract a valid amino-acid sequence from your search.")

    props = analyzer.calculate_physicochemical_properties(sequence)
    props_with_sequence = dict(props)
    props_with_sequence["sequence"] = sequence
    props_with_sequence["length"] = len(sequence)

    rule_predictions = DomainRulesEngine.predict_domain_by_rules(sequence, props_with_sequence)
    dataset_predictions = []
    if dataset_matches:
        first_match = dataset_matches[0]
        dataset_predictions.append(
            {
                "domain": first_match.get("domain") or first_match.get("domain_family") or "Known Protein Record",
                "confidence": 1.0,
                "satisfied_conditions": ["Imported dataset match"],
                "description": first_match.get("function") or "Annotation from the imported FASTA dataset.",
                "score": "dataset",
            }
        )
    all_predictions = sorted(
        dataset_predictions + rule_predictions,
        key=lambda item: item.get("confidence", 0),
        reverse=True,
    )

    confidence = all_predictions[0]["confidence"] if all_predictions else 0.0
    match_type = "dataset_match_and_rule_prediction" if dataset_matches else "rule_based_prediction"

    return {
        "match_type": match_type,
        "query_info": {
            "input_type": validation.get("type", "dataset_text") if validation.get("is_valid") else "dataset_text",
            "analyzed_length": len(sequence),
            "matched_dataset_records": len(dataset_matches),
        },
        "analyzed_sequence": sequence,
        "predictions": dataset_matches,
        "rule_based_predictions": all_predictions,
        "analysis_results": {
            "amino_acid_composition": analyzer.calculate_amino_acid_composition(sequence),
            "physicochemical_properties": props,
            "motifs_found": analyzer.find_motifs(sequence),
            "sequence_complexity": analyzer.calculate_sequence_complexity(sequence),
            "domain_hints": analyzer.detect_domain_hints(sequence),
        },
        "confidence": confidence,
        "warnings": warnings,
    }


def save_search(user_id: Optional[str], query: str, result: Dict):
    digest = query_hash(query)
    top_domain = ""
    if result.get("rule_based_predictions"):
        top_domain = result["rule_based_predictions"][0].get("domain", "")

    if user_id:
        predictions_collection.insert_one(
            {
                "user_id": user_id,
                "query": query,
                "query_hash": digest,
                "result": result,
                "top_domain": top_domain,
                "timestamp": datetime.utcnow(),
            }
        )
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"predictions_count": 1}, "$set": {"last_prediction_at": datetime.utcnow()}},
        )

    popular_collection.update_one(
        {"query_hash": digest},
        {
            "$set": {
                "query": query,
                "query_preview": query[:160],
                "top_domain": top_domain,
                "last_searched": datetime.utcnow(),
            },
            "$inc": {"count": 1},
            "$setOnInsert": {"created_at": datetime.utcnow()},
        },
        upsert=True,
    )


# ---------- PYDANTIC MODELS ----------
class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AdminSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    setup_code: str


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetValidate(BaseModel):
    email: EmailStr
    code: str


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str
    password: str


# ---------- FASTAPI APP ----------
app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def import_dataset_on_startup():
    if proteins_collection.estimated_document_count() == 0:
        summary = import_fasta_files()
        print(f"Imported startup FASTA dataset: {summary}")


# ---------- AUTH ENDPOINTS ----------
@app.post("/api/auth/signup")
async def signup(user: UserSignup):
    email = normalize_email(user.email)
    if find_user_by_email(email):
        raise HTTPException(400, "Email already registered")
    if not validate_password(user.password):
        raise HTTPException(400, "Password must be at least 8 characters with letters and numbers")

    user_id = f"local_{secrets.token_urlsafe(16)}"
    user_doc = {
        "user_id": user_id,
        "email": email,
        "name": user.name.strip() or email.split("@")[0],
        "password_hash": hash_password(user.password),
        "auth_provider": "email",
        "role": "user",
        "is_active": True,
        "predictions_count": 0,
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow(),
    }
    users_collection.insert_one(user_doc)
    token = create_token({"sub": user_id, "email": email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"user_id": user_id, "email": email, "name": user_doc["name"], "role": "user"},
    }


@app.post("/api/admin/signup")
async def admin_signup(user: AdminSignup):
    if not settings.ADMIN_SETUP_CODE:
        raise HTTPException(503, "Admin signup is not configured")
    if not hmac.compare_digest(user.setup_code.strip(), settings.ADMIN_SETUP_CODE):
        raise HTTPException(403, "Invalid admin setup code")

    email = normalize_email(user.email)
    if find_user_by_email(email):
        raise HTTPException(400, "Email already registered")
    if not validate_password(user.password):
        raise HTTPException(400, "Password must be at least 8 characters with letters and numbers")

    user_id = f"admin_{secrets.token_urlsafe(16)}"
    user_doc = {
        "user_id": user_id,
        "email": email,
        "name": user.name.strip() or email.split("@")[0],
        "password_hash": hash_password(user.password),
        "auth_provider": "email",
        "role": "admin",
        "is_active": True,
        "predictions_count": 0,
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow(),
    }
    users_collection.insert_one(user_doc)
    token = create_token({"sub": user_id, "email": email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"user_id": user_id, "email": email, "name": user_doc["name"], "role": "admin"},
    }


@app.post("/api/auth/login")
async def login(user: UserLogin):
    db_user = find_user_by_email(user.email)
    if not db_user or not verify_password(user.password, db_user.get("password_hash", "")):
        raise HTTPException(401, "Invalid email or password")
    if db_user.get("is_active", True) is False:
        raise HTTPException(403, "This account has been disabled")

    users_collection.update_one({"_id": db_user["_id"]}, {"$set": {"last_login": datetime.utcnow()}})
    token = create_token({"sub": db_user["user_id"], "email": db_user["email"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": db_user["user_id"],
            "email": db_user["email"],
            "name": db_user.get("name", db_user["email"].split("@")[0]),
            "picture": db_user.get("picture"),
            "role": db_user.get("role", "user"),
            "is_active": db_user.get("is_active", True),
        },
    }


@app.post("/api/auth/forgot-password")
async def forgot_password(request: PasswordResetRequest):
    if not password_reset_available():
        raise HTTPException(503, "Password reset is not available. Please contact support.")

    user = find_user_by_email(request.email)
    response = {
        "message": "Password reset code has been generated.",
        "expires_minutes": PASSWORD_RESET_EXPIRE_MINUTES,
    }
    if not user:
        return response

    reset_code, _ = create_password_reset_code(user)

    if password_reset_email_enabled():
        try:
            send_password_reset_email(user["email"], reset_code)
            response["delivery"] = "email"
            response["message"] = "Password reset code has been sent to your email."
            logger.info(f"Password reset email sent to {user['email']}")
            return response
        except ValueError as ve:
            logger.warning(f"Email delivery failed for {user['email']}: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")

    response["delivery"] = "code"
    response["code"] = reset_code
    response["message"] = "Password reset code has been generated. Use the code below to continue."
    log_password_reset_code(user["email"], reset_code)
    logger.info(f"Password reset code generated for {user['email']}: {reset_code}")
    return response


@app.post("/api/auth/validate-reset-code")
async def validate_reset_code(request: PasswordResetValidate):
    user, reset_doc = find_matching_password_reset(request.email, request.code, record_failure=False)
    if not user or not reset_doc:
        raise HTTPException(400, "Reset code is invalid or has expired")
    return {"email": user["email"], "expires_at": reset_doc["expires_at"].isoformat()}


@app.post("/api/auth/reset-password")
async def reset_password(request: PasswordResetConfirm):
    if not validate_password(request.password):
        raise HTTPException(400, "Password must be at least 8 characters with letters and numbers")

    user, reset_doc = consume_password_reset_code(request.email, request.code)
    if not user or not reset_doc:
        raise HTTPException(400, "Reset code is invalid or has expired")

    users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"password_hash": hash_password(request.password), "password_changed_at": datetime.utcnow()},
        },
    )
    return {"message": "Password has been reset. You can now log in with your new password."}


@app.post("/api/auth/record-prediction")
async def record_prediction(authorization: str = Header(default=None)):
    user_id = auth_user_id(authorization)
    if user_id:
        users_collection.update_one({"user_id": user_id}, {"$inc": {"predictions_count": 1}})
    return {"success": True}


@app.get("/api/user/profile")
async def get_user_profile(authorization: str = Header(default=None)):
    return public_user_doc(current_user(authorization))


@app.get("/api/admin/users")
async def admin_list_users(authorization: str = Header(default=None)):
    require_admin(authorization)
    users = []
    for user in users_collection.find({}, {"password_hash": 0}).sort("created_at", DESCENDING):
        row = public_user_doc(user)
        row["saved_searches"] = predictions_collection.count_documents({"user_id": user.get("user_id")})
        users.append(row)
    return {
        "users": users,
        "total_users": len(users),
        "active_users": sum(1 for user in users if user.get("is_active", True)),
        "admin_users": sum(1 for user in users if user.get("role") == "admin"),
    }


@app.patch("/api/admin/users/{target_user_id}")
async def admin_update_user(target_user_id: str, update: AdminUserUpdate, authorization: str = Header(default=None)):
    admin = require_admin(authorization)
    target = users_collection.find_one({"user_id": target_user_id})
    if not target:
        raise HTTPException(404, "User not found")

    changes = {}
    if update.name is not None:
        clean_name = update.name.strip()
        if clean_name:
            changes["name"] = clean_name
    if update.role is not None:
        role = update.role.strip().lower()
        if role not in {"user", "admin"}:
            raise HTTPException(400, "Role must be user or admin")
        if target_user_id == admin["user_id"] and role != "admin":
            raise HTTPException(400, "You cannot remove your own admin role")
        changes["role"] = role
    if update.is_active is not None:
        if target_user_id == admin["user_id"] and update.is_active is False:
            raise HTTPException(400, "You cannot disable your own admin account")
        changes["is_active"] = update.is_active

    if not changes:
        return public_user_doc(target)

    changes["updated_at"] = datetime.utcnow()
    users_collection.update_one({"user_id": target_user_id}, {"$set": changes})
    updated = users_collection.find_one({"user_id": target_user_id})
    return public_user_doc(updated)


@app.delete("/api/admin/users/{target_user_id}")
async def admin_delete_user(target_user_id: str, authorization: str = Header(default=None)):
    admin = require_admin(authorization)
    if target_user_id == admin["user_id"]:
        raise HTTPException(400, "You cannot delete your own admin account")
    target = users_collection.find_one({"user_id": target_user_id})
    if not target:
        raise HTTPException(404, "User not found")

    users_collection.delete_one({"user_id": target_user_id})
    predictions_collection.delete_many({"user_id": target_user_id})
    password_resets_collection.delete_many({"user_id": target_user_id})
    return {"message": "User and related account data deleted"}


# ---------- PREDICTION ENDPOINT with saving ----------
@app.post("/api/predict")
async def predict(request: dict, authorization: str = Header(default=None)):
    query = request.get("query", "")
    result = build_prediction_result(query)
    save_search(auth_user_id(authorization), query, result)
    return result


# ---------- HISTORY ENDPOINT ----------
@app.get("/api/predictions/history")
async def get_prediction_history(authorization: str = Header(default=None), limit: int = 20):
    user_id = auth_user_id(authorization)
    if not user_id:
        raise HTTPException(401, "Authentication required")

    cursor = predictions_collection.find({"user_id": user_id}).sort("timestamp", DESCENDING).limit(limit)
    return [jsonable_doc(doc) for doc in cursor]


# ---------- POPULAR SEARCHES ENDPOINT ----------
@app.get("/api/popular-searches")
async def get_popular_searches(limit: int = 10):
    cursor = popular_collection.find({}, {"_id": 0, "query_hash": 0}).sort("count", DESCENDING).limit(limit)
    return [jsonable_doc(doc) for doc in cursor]


# ---------- STATS ENDPOINT ----------
@app.get("/api/stats")
async def get_stats():
    return {
        "total_proteins": proteins_collection.count_documents({}),
        "unique_domains": len(proteins_collection.distinct("domain")),
        "registered_users": users_collection.count_documents({}),
        "saved_searches": predictions_collection.count_documents({}),
        "popular_searches": popular_collection.count_documents({}),
    }


# ---------- OTHER UTILITY ENDPOINTS ----------
@app.post("/api/motif-positions")
async def motif_positions(sequence: str):
    clean_sequence = analyzer.clean_sequence(sequence)
    motifs = []
    for name, starts in analyzer.find_motifs(clean_sequence).items():
        motifs.extend({"name": name, "start": start, "end": start + 1, "color": "#FF6B6B"} for start in starts)
    return {"sequence": clean_sequence, "motifs": motifs, "length": len(clean_sequence)}


@app.post("/api/validate-fasta")
async def validate_fasta(file: UploadFile = File(...)):
    content = await file.read()
    try:
        proteins = FASTAParser.parse_fasta_string(content.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(400, f"Invalid FASTA file: {exc}")
    lengths = [protein["length"] for protein in proteins]
    return {
        "valid": bool(proteins),
        "message": f"Found {len(proteins)} sequences",
        "protein_count": len(proteins),
        "avg_sequence_length": round(sum(lengths) / len(lengths), 1) if lengths else 0,
    }


@app.post("/api/upload-fasta")
async def upload_fasta(file: UploadFile = File(...)):
    content = await file.read()
    try:
        proteins = FASTAParser.parse_fasta_string(content.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(400, f"Invalid FASTA file: {exc}")

    operations = []
    for protein in proteins:
        doc = prepare_protein_doc(protein, source_file=file.filename)
        operations.append(
            UpdateOne(
                {"protein_id": doc["protein_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                upsert=True,
            )
        )

    result = proteins_collection.bulk_write(operations, ordered=False) if operations else None
    return {
        "message": f"Processed {file.filename}",
        "new_proteins_added": result.upserted_count if result else 0,
        "duplicates_skipped": len(operations) - (result.upserted_count if result else 0),
    }


@app.post("/api/batch-predict")
async def batch_predict(file: UploadFile = File(...)):
    content = await file.read()
    proteins = FASTAParser.parse_fasta_string(content.decode("utf-8"))
    results = []
    for protein in proteins:
        prediction = build_prediction_result(protein["sequence"])
        top = prediction["rule_based_predictions"][0] if prediction["rule_based_predictions"] else {}
        results.append(
            {
                "protein_id": protein["protein_id"],
                "protein_name": protein["protein_name"],
                "top_domain": top.get("domain", "Unknown"),
                "top_confidence": top.get("confidence", 0),
            }
        )
    avg_confidence = sum(item["top_confidence"] for item in results) / len(results) if results else 0
    return {
        "summary": {
            "total_proteins": len(results),
            "proteins_with_predictions": sum(1 for item in results if item["top_domain"] != "Unknown"),
            "average_confidence": f"{avg_confidence:.0%}",
        },
        "results": results,
    }


@app.post("/api/import-data")
async def import_data_endpoint(authorization: str = Header(default=None)):
    user_id = auth_user_id(authorization)
    if not user_id:
        raise HTTPException(401, "Authentication required")
    return import_fasta_files()


@app.get("/")
def root():
    return {"message": "Protein Domain Finder API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
