Autonomous Multi Chatbot  — Your Local Multi-Chatbot Platform

It is a powerful, privacy-first platform that lets users create, customize, and manage **multiple intelligent chatbots**, each tailored for a specific **domain, persona, and knowledge base** — all running **100% locally** using LLaMA, FAISS, and smart document parsing.

---

## 🚀 Key Features

### 🧠 Multi-Bot Creation & Management
- Create multiple chatbots, each with a unique role (e.g., “University Assistant”, “Medical Help Bot”, “Shop Assistant”)
- Assign different personalities, knowledge sources, and behaviors
- All bots are isolated with their own context and configuration

### 📁 Upload Private Files
- Attach PDF, CSV, TXT, or DOCX documents to each bot
- Smart table extraction using `pdfplumber`
- Embedding-based search with **FAISS**
- Use as a **local RAG bot** for private files (no cloud, no leaks)

### 💬 Custom Instruction & Role Design
- Set a system prompt and fine-tune the behavior
- Create assistants, advisors, support bots, or even role-playing agents

### 🎨 Full UI Customization per Bot
- Users can personalize:
  - Chat background color
  - User & bot message bubble colors
  - Button styling
  - Bot avatar/image
  - Font style & size
- Ideal for embedding in websites or internal dashboards with branding needs

### 🔒 100% Local Privacy
- All data, models, and logic stay **on your device**
- Powered by **Ollama** for local LLaMA/Mistral inference
- No internet, no cloud APIs, no tracking

---

## ⚙️ Architecture Overview

```plaintext
[User Dashboard] ───▶ [Bot Manager]
                     ├── Custom Instructions
                     ├── Theme Settings
                     ├── Document Uploads
                     └── Chat UI per Bot
                                 │
                      ┌──────────┼───────────┐
                      ▼                      ▼
            [Embedding Pipeline]       [LLaMA/Mistral LLM]
            (pdfplumber + FAISS)       (via Ollama, CPU/Local)
                      ▼                      ▲
              [Relevant Context] ──▶ [Answer Generation]


🛠️ Tech Stack
| Layer          | Tool                       |
| -------------- | -------------------------- |
| UI / Dashboard | Streamlit / React (custom) |
| Backend API    | FastAPI / Flask            |
| LLM Runtime    | Ollama (LLaMA / Mistral)   |
| Embeddings     | `sentence-transformers`    |
| Vector DB      | FAISS                      |
| PDF Parsing    | `pdfplumber` (for tables)  |
| Local Storage  | Filesystem / JSON DB       |

🧪 Use Cases
| Domain              | Description                                              |
| ------------------- | -------------------------------------------------------- |
| 🎓 Education        | Admission assistant chatbot for university websites      |
| 🛒 E-Commerce       | Product search or customer support bot on shopping sites |
| 🏥 Healthcare       | Private clinical data chatbot for doctors                |
| 🧑‍💼 HR/Enterprise | Internal policy or document question-answering bots      |
| 🔐 Personal Vault   | Local Q\&A over confidential files, never leaving device |

🧰 Installation
git clone https://github.com/yourusername/OneFileBot.git
cd OneFileBot

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Ollama (install llama/mistral models as needed)
ollama run llama3  # Or: ollama run mistral

# Run the app
python app.py  # Or: streamlit run dashboard.py

Linkedin Post: https://www.linkedin.com/posts/lakshay-malik-00at_localfirst-privacybydesign-llm-activity-7339337082949050369-U9PZ?utm_source=share&utm_medium=member_desktop&rcm=ACoAAD3LgY0BdZVD0X65Zd5JnmsoDSApAESXKB0

Ui Interface
<img width="935" height="967" alt="image" src="https://github.com/user-attachments/assets/4243810d-a4cf-4218-a47e-b5c5d021ecbc" />

<img width="1807" height="731" alt="image" src="https://github.com/user-attachments/assets/165c771b-3e2e-496e-9dda-7415175fe173" />

<img width="954" height="978" alt="image" src="https://github.com/user-attachments/assets/cc0f899c-7c89-4733-846c-b63d7bd0bb1f" />


