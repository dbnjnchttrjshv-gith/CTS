# 🌱 SproutBot - AI Gardening & Plant Care Assistant

![SproutBot Demo](sproutbot_demo.gif)

**SproutBot** is an agentic AI plant care and nursery assistant built on Google Cloud ADK (Agent Development Kit), Gemini models, and the Agent Platform. It manages indoor plant collections, diagnoses plant health issues, tracks watering schedules, generates plant imagery, and locates nearby garden nurseries.

---

## 🚀 Wired Cloud Services & Capabilities

SproutBot relies strictly on verified Google Cloud and API integrations wired up in `app/agent.py` and `app/tools.py`:

* **🧠 Vertex AI Memory Bank Service**: Connected to Agent Engine ID (`1955817880557715456`). Uses `PreloadMemoryTool` and durable session callbacks to remember user preferences, indoor plant collections, and critical allergy disclosures across turns.
* **🔥 Google Cloud Firestore**: Reads and updates the `plants` collection in project `qwiklabs-gcp-01-41fd6d52d172` to manage plant care requirements, last watered dates, and schedule alerts.
* **☁️ Google Cloud Storage (GCS)**: Stores generated media assets in public bucket `sproutbot-media-qwiklabs-gcp-01-41fd6d52d172`.
* **🖼️ Vertex AI Image Generation**: Uses `gemini-3.1-flash-lite-image` in the `global` region to generate plant visuals, saving Playground artifacts via `ToolContext` and uploading public HTTPS image URLs to GCS.
* **💻 Agent Engine Sandbox Code Executor**: Runs Python code snippets inside an isolated Agent Engine execution sandbox for botanical and growth calculations.
* **🎨 A2UI Protocol (v0.8 Basic Catalog)**: Outputs rich, structured surface specs (Cards, Columns, Rows, Text, Images, and Status Badges) transformed dynamically by `a2ui_callback`.
* **📍 Google Maps Platform**: Integrates the Geocoding API and Places API (New) to locate nearby plant nurseries, florists, and garden centers.
* **🌿 iNaturalist Biodiversity API**: Searches real-world species taxonomy, scientific names, and reference photos.
* **🌤️ Ambient Climate Advisory**: Evaluates local temperature and relative humidity to adjust watering schedules.

---

## 📋 Status & Planned Features

* **Implemented**: Catalog management, watering schedule alerts, Firestore persistence, GCS uploads, image generation, A2UI surface rendering, location/nursery search, ambient climate advisory, and Memory Bank persistence.
* **Planned / Not Yet Implemented**: Omni model short video generation (`gemini-omni-flash-preview`).

---

## 🛠️ Local Setup & Running Instructions

### Prerequisites
* Python 3.11+
* Google Cloud SDK (`gcloud`) authenticated with Application Default Credentials

### 1. Install Project Dependencies
```bash
uv pip install -r requirements.txt
```

### 2. Start the Agent Playground (Local ADK Server)
```bash
uv run adk web . --port 8000 --reload_agents --memory_service_uri=agentengine://1955817880557715456
```

### 3. Start the Custom Web Frontend
In a separate terminal window:
```bash
cd frontend
uv pip install -r requirements.txt
AGENT_ENGINE_RESOURCE_NAME="projects/251759604911/locations/us-east1/reasoningEngines/8706150772032667648" AGENT_DIRECTORY="app" PORT=8080 uv run python main.py
```

---

## 🚢 Cloud Run Deployment

To deploy the FastAPI frontend proxy to Google Cloud Run:
```bash
gcloud run deploy sproutbot-frontend \
  --source ./frontend \
  --region us-east1 \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="projects/251759604911/locations/us-east1/reasoningEngines/8706150772032667648",AGENT_DIRECTORY="app" \
  --allow-unauthenticated
```
