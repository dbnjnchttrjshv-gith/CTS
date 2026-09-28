# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    add_new_plant,
    check_watering_schedule_alerts,
    fetch_ambient_climate,
    find_nearby_places,
    generate_plant_image,
    geocode_address,
    list_plants_catalog,
    lookup_plant_care,
    search_botanical_species_info,
    update_plant_watering,
)

# Load remote_agent_runtime_id from deployment_metadata.json
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None
memory_bank_id = "1955817880557715456"

if metadata_path.exists():
    with open(metadata_path, "r") as f:
        meta = json.load(f)
        agent_engine_resource_name = meta.get("remote_agent_runtime_id")
        if agent_engine_resource_name:
            memory_bank_id = agent_engine_resource_name.split("/")[-1]

code_executor = None
if agent_engine_resource_name:
    code_executor = AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=agent_engine_resource_name
    )

# WRITE: Callback to automatically extract and save durable session memories after each turn
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None

# Memory service builder for deployment
def memory_service_builder():
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-01-41fd6d52d172",
        location="us-east1",
        agent_engine_id=memory_bank_id,
    )

# Build A2UI v0.8 System Prompt with Basic Catalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description="SproutBot, an expert AI Plant Care and Nursery Assistant.",
    workflow_description="Analyze the user request, call tools when needed to fetch real plant care data, nurseries, photos, or climate data, and return structured A2UI UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects. "
        "You assist plant owners with caring for their indoor plant collection, checking plant health, updating watering schedules, finding nearby plant nurseries or garden centers, generating plant photos/visuals, and executing Python calculations in a sandbox. "
        "You remember all user preferences, health facts, and critical personal details across conversations — ESPECIALLY ALL USER ALLERGIES (such as pollen allergies, plant sap/latex sensitivities, mold/fungus allergies, or plant toxicities). Always recall and apply stored allergy information when recommending plants, diagnosing issues, or providing care instructions to keep the user safe."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        list_plants_catalog,
        lookup_plant_care,
        update_plant_watering,
        add_new_plant,
        check_watering_schedule_alerts,
        fetch_ambient_climate,
        search_botanical_species_info,
        geocode_address,
        find_nearby_places,
        generate_plant_image,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
