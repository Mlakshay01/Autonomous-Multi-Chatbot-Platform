import os
import json
import faiss
import pickle
import uuid
import numpy as np
import requests
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# --- Directories ---
UPLOAD_FOLDER = "uploaded_files"
EMBED_FOLDER = "embeddings"
BOT_CONFIG_FOLDER = "bot_configs" 
STATIC_FOLDER = "static"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EMBED_FOLDER, exist_ok=True)
os.makedirs(BOT_CONFIG_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# --- Allowed upload file types ---
ALLOWED_EXTENSIONS = {"json", "txt", "md", "csv", "pdf"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

# --- Ollama config ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# --- Embedding model ---
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- In-memory stores ---
bot_configs = {}     # bot_name -> config dict
chat_histories = {}  # session_id -> list of chat messages
bot_themes = {}      # bot_name -> theme dict
cached_indexes = {}  # bot_name -> (faiss_index, metadata_list)

# --- Default UI theme (updated to include inputTextColor) ---
DEFAULT_THEME = {
    "backgroundColor": "#ffffff",
    "textColor": "#222222",
    "buttonColor": "#4a90e2",
    "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    "botMessageBackgroundColor": "#000000",
    "userMessageBackgroundColor": "#55882D",
    "inputBackgroundColor": "#ffffff",     
    "inputBorderColor": "#cccccc",
    "inputTextColor": "#000000"  # Added input text color to default theme
}

def allowed_file(filename):
    """Check if filename extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    """Check if filename extension is allowed for images."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

import pdfplumber

def process_uploaded_file(filepath):
    """
    Extract tabular data from PDFs (employee transfers), or handle JSON fallback.
    Build embeddings and store index + metadata.
    """
    texts = []
    metadatas = []

    ext = filepath.rsplit('.', 1)[-1].lower()

    if ext == "pdf":
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if any(row):
                            row_text = " | ".join(cell.strip() if cell else "" for cell in row)
                            texts.append(row_text)
                            metadatas.append({
                                "title": row[0].strip() if row[0] else "Row",
                                "description": row_text,
                                "phase": ""
                            })

    elif ext == "json":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "phases" in data:
            for phase in data["phases"]:
                phase_name = phase.get("phase", "")
                for node in phase.get("nodes", []):
                    title = node.get("title", "")
                    desc = node.get("description", "")
                    full_text = f"{title}: {desc}"
                    texts.append(full_text)
                    metadatas.append({
                        "title": title,
                        "description": desc,
                        "phase": phase_name
                    })
        else:
            def extract_texts(obj):
                if isinstance(obj, dict):
                    for v in obj.values():
                        extract_texts(v)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_texts(item)
                elif isinstance(obj, str):
                    texts.append(obj)

            extract_texts(data)
            metadatas = [{"title": "", "description": t, "phase": ""} for t in texts]

    else:
        raise ValueError("Unsupported file format")

    if not texts:
        raise ValueError("No textual data extracted")

    # Embedding logic remains unchanged
    embeddings = embedding_model.encode(texts, show_progress_bar=False)
    embeddings = np.array(embeddings).astype('float32')

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    base_name = os.path.splitext(os.path.basename(filepath))[0] + "_" + uuid.uuid4().hex
    index_path = os.path.join(EMBED_FOLDER, f"{base_name}_index.faiss")
    meta_path = os.path.join(EMBED_FOLDER, f"{base_name}_metadata.pkl")

    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(metadatas, f)

    return index_path, meta_path



def save_bot_config(bot_name, config):
    """Persist bot config to JSON file inside bot's own folder."""
    bot_folder = os.path.join(BOT_CONFIG_FOLDER, bot_name)
    os.makedirs(bot_folder, exist_ok=True)
    path = os.path.join(bot_folder, f"{bot_name}.json")
    with open(path, "w") as f:
        json.dump(config, f, indent=2)

def load_all_bots():
    """Load all saved bot configs from subfolders and preload indexes."""
    for bot_name in os.listdir(BOT_CONFIG_FOLDER):
        bot_folder = os.path.join(BOT_CONFIG_FOLDER, bot_name)
        if os.path.isdir(bot_folder):
            json_path = os.path.join(bot_folder, f"{bot_name}.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    config = json.load(f)
                    bot_configs[bot_name] = config
                    # Ensure theme has all required properties including inputTextColor
                    bot_themes[bot_name] = {**DEFAULT_THEME, **bot_themes.get(bot_name, {})}
                    try:
                        index = faiss.read_index(config["index_path"])
                        with open(config["meta_path"], "rb") as mf:
                            metadata = pickle.load(mf)
                        cached_indexes[bot_name] = (index, metadata)
                        print(f"[INFO] Loaded bot '{bot_name}' with avatar: {config.get('avatar')}")
                    except Exception as e:
                        print(f"[ERROR] Failed to load FAISS index or metadata for '{bot_name}': {e}")

@app.route("/admin/upload", methods=["POST"])
def upload_file():
    # Get form data
    bot_name = request.form.get("bot_name", "").strip()
    bot_role = request.form.get("bot_role", "").strip()
    
    if not bot_name or not bot_role:
        return jsonify({"error": "bot_name and bot_role are required"}), 400
    
    # Secure the bot name
    bot_name = secure_filename(bot_name).replace('.', '_')
    
    # Create bot folder
    bot_folder = os.path.join(BOT_CONFIG_FOLDER, bot_name)
    os.makedirs(bot_folder, exist_ok=True)
    
    # Handle knowledge base file (required for new bots)
    kb_file = request.files.get("file")
    index_path = None
    meta_path = None
    kb_filename = None
    
    # If this is an existing bot and no new file is provided, keep the old file info
    if bot_name in bot_configs and (not kb_file or kb_file.filename == ""):
        # Use existing knowledge base info
        existing_config = bot_configs[bot_name]
        index_path = existing_config["index_path"]
        meta_path = existing_config["meta_path"]
        kb_filename = existing_config["file"]
    else:
        # New file is required
        if not kb_file or kb_file.filename == "":
            return jsonify({"error": "Knowledge base file is required"}), 400
        
        if not allowed_file(kb_file.filename):
            return jsonify({"error": "Knowledge base file type not allowed"}), 400
        
        # Save knowledge base file
        kb_filename = f"{uuid.uuid4().hex}_{secure_filename(kb_file.filename)}"
        kb_filepath = os.path.join(UPLOAD_FOLDER, kb_filename)
        kb_file.save(kb_filepath)
        
        # Process knowledge base file (index + metadata)
        try:
            index_path, meta_path = process_uploaded_file(kb_filepath)
        except Exception as e:
            return jsonify({"error": f"Failed to process knowledge base file: {str(e)}"}), 400
    
    # Handle avatar file (optional)
    avatar_file = request.files.get("bot_avatar")  # Note: using "bot_avatar" as per HTML form
    avatar_filename = None
    
    if avatar_file and avatar_file.filename != "":
        if not allowed_image_file(avatar_file.filename):
            return jsonify({"error": "Avatar file type not allowed. Use png, jpg, jpeg, gif, webp, or svg"}), 400
        
        # Create unique avatar filename to avoid conflicts
        file_ext = avatar_file.filename.rsplit('.', 1)[1].lower()
        avatar_filename = f"avatar_{uuid.uuid4().hex}.{file_ext}"
        avatar_path = os.path.join(bot_folder, avatar_filename)
        
        try:
            avatar_file.save(avatar_path)
            print(f"[INFO] Avatar saved to: {avatar_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save avatar: {e}")
            return jsonify({"error": f"Failed to save avatar: {str(e)}"}), 500
    else:
        # Keep existing avatar if updating bot
        if bot_name in bot_configs:
            avatar_filename = bot_configs[bot_name].get("avatar")
    
    # Cleanup old files if bot exists and we're replacing them
    if bot_name in bot_configs:
        old_config = bot_configs[bot_name]
        
        # Clean up old knowledge base files if we have new ones
        if kb_file and kb_file.filename != "":
            try:
                if os.path.exists(old_config["index_path"]):
                    os.remove(old_config["index_path"])
                if os.path.exists(old_config["meta_path"]):
                    os.remove(old_config["meta_path"])
                old_file_path = os.path.join(UPLOAD_FOLDER, old_config["file"])
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except Exception as e:
                print(f"[WARNING] Failed to cleanup old files: {e}")
        
        # Clean up old avatar if we have a new one
        if avatar_file and avatar_file.filename != "":
            old_avatar = old_config.get("avatar")
            if old_avatar:
                old_avatar_path = os.path.join(bot_folder, old_avatar)
                if os.path.exists(old_avatar_path) and old_avatar != avatar_filename:
                    try:
                        os.remove(old_avatar_path)
                    except Exception as e:
                        print(f"[WARNING] Failed to remove old avatar: {e}")
        
        # Clear cached index
        cached_indexes.pop(bot_name, None)
    
    # Create/update bot config
    bot_configs[bot_name] = {
        "role": bot_role,
        "file": kb_filename,
        "index_path": index_path,
        "meta_path": meta_path,
        "avatar": avatar_filename  # This will be None if no avatar
    }
    
    # Ensure bot has theme with inputTextColor
    if bot_name not in bot_themes:
        bot_themes[bot_name] = DEFAULT_THEME.copy()
    else:
        # Ensure existing themes have the new inputTextColor property
        bot_themes[bot_name] = {**DEFAULT_THEME, **bot_themes[bot_name]}
    
    # Save bot config to JSON file
    try:
        save_bot_config(bot_name, bot_configs[bot_name])
        print(f"[INFO] Bot config saved for '{bot_name}': {bot_configs[bot_name]}")
    except Exception as e:
        print(f"[ERROR] Failed to save bot config: {e}")
        return jsonify({"error": f"Failed to save bot config: {str(e)}"}), 500
    
    return jsonify({"message": f"Bot '{bot_name}' uploaded and ready."})

@app.route("/bot/<bot_name>/avatar")
def get_bot_avatar(bot_name):
    """Serve bot avatar image"""
    if bot_name not in bot_configs:
        return "Bot not found", 404
    
    config = bot_configs[bot_name]
    avatar_filename = config.get("avatar")
    
    if avatar_filename:
        bot_folder = os.path.join(BOT_CONFIG_FOLDER, bot_name)
        avatar_path = os.path.join(bot_folder, avatar_filename)
        
        if os.path.exists(avatar_path):
            return send_from_directory(bot_folder, avatar_filename)
        else:
            print(f"[WARNING] Avatar file not found: {avatar_path}")
    
    # Return default avatar if none is set or file doesn't exist
    default_avatar_path = os.path.join(STATIC_FOLDER, "default-avatar.png")
    if os.path.exists(default_avatar_path):
        return send_from_directory(STATIC_FOLDER, "default-avatar.png")
    else:
        return "No avatar available", 404

@app.route("/chat/<bot_name>", methods=["POST"])
def chat(bot_name):
    if bot_name not in bot_configs:
        return jsonify({"error": "Bot not found"}), 404

    data = request.get_json(force=True)
    user_query = data.get("query", "").strip()
    session_id = data.get("session_id", "").strip()

    if not user_query or not session_id:
        return jsonify({"error": "Both 'query' and 'session_id' are required."}), 400

    config = bot_configs[bot_name]
    role = config["role"]

    # Load or get cached faiss index and metadata
    if bot_name not in cached_indexes:
        try:
            index = faiss.read_index(config["index_path"])
            with open(config["meta_path"], "rb") as f:
                metadata = pickle.load(f)
            cached_indexes[bot_name] = (index, metadata)
        except Exception as e:
            return jsonify({"error": f"Failed to load index or metadata: {str(e)}"}), 500
    else:
        index, metadata = cached_indexes[bot_name]

    # Embed query
    query_vector = embedding_model.encode([user_query])
    query_vector = np.array(query_vector).astype('float32')

    # Search for top 10 closest entries
    D, I = index.search(query_vector, 10)

    # Distance threshold to decide if context is relevant enough (tune as needed)
    DISTANCE_THRESHOLD = 1.5
    closest_distance = D[0][0]

    if closest_distance > DISTANCE_THRESHOLD:
        response_text = (
            f"🤖 I'm not confident about that based on the current knowledge base.\n"
            f"(Closest match distance: {closest_distance:.2f})\n"
            f"Please try rephrasing or ask something related to: {role}."
        )
    else:
        # Build knowledge base context from metadata
        retrieved_texts = []
        for idx in I[0]:
            if 0 <= idx < len(metadata):
                md = metadata[idx]
                # Include phase if present
                phase = f" (Phase: {md.get('phase')})" if md.get('phase') else ""
                title = md.get("title", "").strip()
                desc = md.get("description", "").strip()
                entry_text = f"{title}{phase}: {desc}" if title else desc
                retrieved_texts.append(entry_text)

        kb_context = "\n".join(retrieved_texts)

        # Retrieve or init chat history for session
        history = chat_histories.get(session_id, [])
        history.append({"role": "user", "content": user_query})
        # Keep last 4 messages max (user + assistant)
        if len(history) > 8:
            history = history[-8:]

        # Format conversation history text for prompt
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])

        prompt = f"""
You are a smart, friendly, and unisex digital assistant. You're always helpful, respectful, and clear — like a real human guide.

You specialize in this area: {role}

Use ONLY the information from the knowledge base below to answer the user's query. If something is missing or unclear, say so politely and offer to help further.

Speak in a natural, kind, and warm tone — not robotic or overly formal. Be conversational.

Make sure to:
- Greet the user warmly and acknowledge their query.
- Give complete, accurate, and contextually relevant answers based on the knowledge base.
- Never confuse things like emails and URLs — explain them correctly.
- Avoid guessing. If something is unclear, say so and suggest a next step.
- If the context is incomplete, ask helpful follow-up questions such as:
  • "Would you like me to explain more about that?"
  • "Are you looking for eligibility details, steps, or deadlines?"
  • "Do you want a direct link or a summarized overview?"

Remember:
→ If you cannot find the answer in the knowledge base, say: "I'm not fully sure based on the available info. Would you like me to guide you another way?"

---
Knowledge Base:
{kb_context}
---
Conversation History:
{history_text}
---
User Query:
{user_query}
---

Now respond to the user naturally and helpfully — like a smart assistant who cares about solving their problem.
"""

        try:
            resp = requests.post(
                OLLAMA_API_URL,
                json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_gpu": 0  # Force CPU usage
                }},
            )

            if resp.status_code == 200:
                response_json = resp.json()
                response_text = response_json.get("response", "Sorry, no response from model.")
            else:
                response_text = f"❌ Ollama error {resp.status_code}: {resp.text}"
        except Exception as e:
            response_text = f"❌ Ollama connection failed: {str(e)}"

        # Append assistant response to history and save
        history.append({"role": "assistant", "content": response_text})
        chat_histories[session_id] = history

    return jsonify({"response": response_text})

@app.route("/bots", methods=["GET"])
def list_bots():
    """Return bot configs (name, role, file info)."""
    # Return bot configs with only public info (no index or meta paths)
    public_configs = {
        name: {"role": cfg["role"], "file": cfg["file"], "avatar": cfg.get("avatar")}
        for name, cfg in bot_configs.items()
    }
    return jsonify(public_configs)

@app.route("/files/<filename>")
def serve_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})

@app.route("/theme/<bot_name>", methods=["GET"])
def get_theme(bot_name):
    """Get theme for a specific bot, ensuring all properties are present."""
    theme = bot_themes.get(bot_name, DEFAULT_THEME.copy())
    # Ensure theme has all required properties including inputTextColor
    complete_theme = {**DEFAULT_THEME, **theme}
    return jsonify(complete_theme)

@app.route("/theme/<bot_name>", methods=["POST"])
def update_theme(bot_name):
    """Update theme for a specific bot, including inputTextColor."""
    if bot_name not in bot_configs:
        return jsonify({"error": "Bot not found"}), 404

    data = request.get_json(force=True)
    theme = bot_themes.get(bot_name, DEFAULT_THEME.copy())

    # Update all theme properties that are provided in the request
    for key in DEFAULT_THEME.keys():
        if key in data:
            theme[key] = data[key]

    bot_themes[bot_name] = theme
    
    print(f"[INFO] Theme updated for '{bot_name}': {theme}")
    
    return jsonify({"message": "Theme updated", "theme": theme})

@app.route("/delete_bot/<bot_name>", methods=["DELETE"])
def delete_bot(bot_name):
    if bot_name not in bot_configs:
        return jsonify({"error": "Bot not found"}), 404

    config = bot_configs[bot_name]
    bot_folder = os.path.join(BOT_CONFIG_FOLDER, bot_name)

    try:
        # Remove knowledge base files
        if os.path.exists(config["index_path"]):
            os.remove(config["index_path"])
        if os.path.exists(config["meta_path"]):
            os.remove(config["meta_path"])
        
        kb_file_path = os.path.join(UPLOAD_FOLDER, config["file"])
        if os.path.exists(kb_file_path):
            os.remove(kb_file_path)
        
        # Remove bot config file
        config_file_path = os.path.join(bot_folder, f"{bot_name}.json")
        if os.path.exists(config_file_path):
            os.remove(config_file_path)
        
        # Remove avatar if exists
        avatar_filename = config.get("avatar")
        if avatar_filename:
            avatar_path = os.path.join(bot_folder, avatar_filename)
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
        
        # Remove bot folder if empty
        if os.path.exists(bot_folder) and not os.listdir(bot_folder):
            os.rmdir(bot_folder)
            
    except Exception as e:
        print(f"Delete error: {e}")

    # Clean up in-memory stores
    bot_configs.pop(bot_name, None)
    cached_indexes.pop(bot_name, None)
    chat_histories.pop(bot_name, None)
    bot_themes.pop(bot_name, None)

    return jsonify({"message": f"Bot '{bot_name}' deleted."})

@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

# Load all existing bots on startup
load_all_bots()

if __name__ == "__main__":
    # For production consider using gunicorn + nginx
    app.run(debug=True, port=5000)