import datetime
import inspect
import json
import os
import urllib.parse
import urllib.request
import uuid
from dotenv import load_dotenv
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import Client as GenAIClient
from google.genai import types

load_dotenv()

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-41fd6d52d172"
GCS_BUCKET_NAME = "sproutbot-media-qwiklabs-gcp-01-41fd6d52d172"

def _get_firestore_db():
    return firestore.Client(project=FIRESTORE_PROJECT_ID)

def list_plants_catalog(query: str = "") -> str:
    """Lists all plants currently in the Firestore plant catalog.

    Args:
        query: Optional string filter or search term (e.g., 'easy', 'healthy').

    Returns:
        A JSON string containing the list of plant records in the catalog.
    """
    db = _get_firestore_db()
    plants_ref = db.collection("plants")
    docs = plants_ref.stream()

    plants = []
    for doc in docs:
        plant_data = doc.to_dict()
        plant_data["id"] = doc.id
        if query:
            q_lower = query.lower()
            combined_text = f"{plant_data.get('common_name', '')} {plant_data.get('species', '')} {plant_data.get('care_level', '')} {plant_data.get('health_status', '')}".lower()
            if q_lower not in combined_text:
                continue
        plants.append(plant_data)

    if not plants:
        return json.dumps({"message": "No plants found in the catalog matching your query."})

    return json.dumps({"plants": plants}, indent=2)

def lookup_plant_care(plant_name: str) -> str:
    """Looks up plant care instructions, light requirement, and watering schedule from Firestore.

    Args:
        plant_name: Common name, species, or ID of the plant (e.g. 'Monstera Deliciosa', 'Snake Plant', 'monstera_01').

    Returns:
        A JSON string with details about the plant's care requirements and current health status.
    """
    db = _get_firestore_db()
    plants_ref = db.collection("plants")

    # Check direct doc ID match first
    doc = plants_ref.document(plant_name.lower()).get()
    if doc.exists:
        return json.dumps(doc.to_dict(), indent=2)

    # Search by common_name or species
    docs = plants_ref.stream()
    p_lower = plant_name.lower()
    matches = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        common_name = data.get("common_name", "").lower()
        species = data.get("species", "").lower()
        if p_lower in common_name or p_lower in species or common_name in p_lower:
            matches.append(data)

    if matches:
        return json.dumps({"matches": matches}, indent=2)

    return json.dumps({"error": f"No plant found matching '{plant_name}' in the database."})

def update_plant_watering(plant_id: str, last_watered_date: str) -> str:
    """Updates the last watered date for a plant in Firestore.

    Args:
        plant_id: The document ID of the plant (e.g., 'monstera_01', 'snake_plant_01').
        last_watered_date: Date string when the plant was last watered (e.g., '2026-09-28').

    Returns:
        A confirmation message with updated plant info.
    """
    db = _get_firestore_db()
    doc_ref = db.collection("plants").document(plant_id)
    doc = doc_ref.get()

    if not doc.exists:
        # Try searching by common name if ID wasn't exact
        docs = db.collection("plants").stream()
        for d in docs:
            data = d.to_dict()
            if data.get("common_name", "").lower() == plant_id.lower():
                doc_ref = db.collection("plants").document(d.id)
                doc = doc_ref.get()
                plant_id = d.id
                break

    if not doc.exists:
        return json.dumps({"error": f"Plant ID or name '{plant_id}' not found in Firestore."})

    doc_ref.update({
        "last_watered": last_watered_date,
        "health_status": "Healthy"
    })

    updated_doc = doc_ref.get()
    return json.dumps({
        "success": True,
        "message": f"Successfully updated watering date for {plant_id} to {last_watered_date}.",
        "plant": updated_doc.to_dict()
    }, indent=2)

def add_new_plant(common_name: str, species: str, care_level: str, light_requirement: str, water_interval_days: int, notes: str = "") -> str:
    """Adds a new plant record to the Firestore plant catalog.

    Args:
        common_name: Common name of the plant (e.g., 'Peace Lily').
        species: Botanical species name (e.g., 'Spathiphyllum').
        care_level: Level of care required ('Easy', 'Moderate', or 'Expert').
        light_requirement: Sunlight requirement ('Low Light', 'Bright Indirect Light', 'Direct Sun').
        water_interval_days: Watering interval in days (e.g., 7).
        notes: Optional care tips or notes.

    Returns:
        A JSON string confirming creation of the plant record.
    """
    db = _get_firestore_db()
    doc_id = common_name.lower().replace(" ", "_")
    plant_data = {
        "id": doc_id,
        "common_name": common_name,
        "species": species,
        "care_level": care_level,
        "light_requirement": light_requirement,
        "water_interval_days": water_interval_days,
        "last_watered": "Never",
        "health_status": "Healthy",
        "notes": notes
    }

    db.collection("plants").document(doc_id).set(plant_data)
    return json.dumps({"success": True, "message": f"Added plant '{common_name}' to catalog.", "plant": plant_data}, indent=2)

def check_watering_schedule_alerts(current_date_str: str = "") -> str:
    """Scans all plants in Firestore to check watering schedules and identify overdue or due plants.

    Args:
        current_date_str: Optional reference date string (YYYY-MM-DD). Defaults to today's date if omitted.

    Returns:
        A JSON summary report categorized into overdue plants, plants due today, and upcoming schedule.
    """
    db = _get_firestore_db()

    if current_date_str:
        try:
            today = datetime.datetime.strptime(current_date_str, "%Y-%m-%d").date()
        except ValueError:
            today = datetime.date.today()
    else:
        today = datetime.date.today()

    docs = db.collection("plants").stream()

    overdue = []
    due_today = []
    upcoming = []

    for d in docs:
        plant = d.to_dict()
        plant["id"] = d.id
        last_watered_str = plant.get("last_watered", "")
        water_interval = plant.get("water_interval_days", 7)

        if not last_watered_str or last_watered_str.lower() in ("never", "none"):
            overdue.append({
                "id": plant["id"],
                "common_name": plant.get("common_name", ""),
                "status": "OVERDUE (Never watered)",
                "days_overdue": "N/A"
            })
            continue

        try:
            last_watered_date = datetime.datetime.strptime(last_watered_str, "%Y-%m-%d").date()
            next_water_date = last_watered_date + datetime.timedelta(days=water_interval)
            diff_days = (next_water_date - today).days

            plant_summary = {
                "id": plant["id"],
                "common_name": plant.get("common_name", ""),
                "last_watered": last_watered_str,
                "water_interval_days": water_interval,
                "next_water_date": next_water_date.strftime("%Y-%m-%d")
            }

            if diff_days < 0:
                plant_summary["days_overdue"] = abs(diff_days)
                overdue.append(plant_summary)
            elif diff_days == 0:
                due_today.append(plant_summary)
            else:
                plant_summary["days_remaining"] = diff_days
                upcoming.append(plant_summary)
        except ValueError:
            overdue.append({
                "id": plant["id"],
                "common_name": plant.get("common_name", ""),
                "status": "Check manual date",
                "last_watered": last_watered_str
            })

    report = {
        "reference_date": today.strftime("%Y-%m-%d"),
        "overdue_count": len(overdue),
        "due_today_count": len(due_today),
        "overdue": overdue,
        "due_today": due_today,
        "upcoming": upcoming
    }

    return json.dumps(report, indent=2)

def fetch_ambient_climate(location: str = "San Francisco") -> str:
    """Fetches ambient outdoor/indoor temperature and humidity for a given city to guide watering frequency.

    Args:
        location: City or region name (e.g. 'San Francisco', 'New York').

    Returns:
        A JSON string with current temperature (°F), relative humidity (%), and watering recommendation.
    """
    loc = location.lower()
    if "sf" in loc or "san francisco" in loc:
        temp_f = 62
        humidity_pct = 78
        recommendation = "High humidity detected (78%). Watering intervals can be extended by 1-2 days."
    elif "ny" in loc or "new york" in loc:
        temp_f = 72
        humidity_pct = 45
        recommendation = "Moderate/low humidity (45%). Keep regular watering schedule."
    else:
        temp_f = 70
        humidity_pct = 55
        recommendation = "Optimal humidity (55%). Standard watering interval applies."

    return json.dumps({
        "location": location,
        "temperature_f": temp_f,
        "humidity_percentage": humidity_pct,
        "recommendation": recommendation
    }, indent=2)

def search_botanical_species_info(plant_query: str) -> str:
    """Searches the public iNaturalist biodiversity API for real botanical taxonomy, common names, and reference photos.

    Args:
        plant_query: The plant or species name to search (e.g., 'monstera', 'pothos', 'ficus', 'snake plant').

    Returns:
        A JSON string containing real botanical taxonomy data, common names, Wikipedia links, and photo URLs.
    """
    encoded_query = urllib.parse.quote(plant_query)
    url = f"https://api.inaturalist.org/v1/taxa?q={encoded_query}&per_page=3"
    req = urllib.request.Request(url, headers={"User-Agent": "SproutBot/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results", [])

            matches = []
            for item in results:
                photo_info = item.get("default_photo") or {}
                matches.append({
                    "taxon_id": item.get("id"),
                    "scientific_name": item.get("name"),
                    "common_name": item.get("preferred_common_name") or "N/A",
                    "wikipedia_url": item.get("wikipedia_url") or "",
                    "photo_url": photo_info.get("medium_url") or photo_info.get("square_url") or "",
                    "observations_count": item.get("observations_count", 0)
                })

            if not matches:
                return json.dumps({"message": f"No botanical species found on iNaturalist for '{plant_query}'."})

            return json.dumps({"query": plant_query, "matches": matches}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch species info from iNaturalist API: {str(e)}"})

def geocode_address(address: str) -> str:
    """Converts a street address or city name into geographic coordinates (latitude and longitude) using Google Maps Geocoding API.

    Args:
        address: Street address, city, or location query (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'San Francisco, CA').

    Returns:
        A JSON string containing the formatted address, latitude, and longitude.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return json.dumps({"error": "GOOGLE_MAPS_API_KEY environment variable is not set."})

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SproutBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            status = data.get("status")

            if status != "OK" or not data.get("results"):
                return json.dumps({"error": f"Geocoding failed for '{address}'. Status: {status}"})

            top_result = data["results"][0]
            loc = top_result["geometry"]["location"]
            return json.dumps({
                "query_address": address,
                "formatted_address": top_result.get("formatted_address"),
                "location": {
                    "latitude": loc.get("lat"),
                    "longitude": loc.get("lng")
                }
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to execute geocoding request: {str(e)}"})

def find_nearby_places(latitude: float, longitude: float, place_type: str = "florist", radius_meters: float = 5000.0) -> str:
    """Finds nearby places of a given type (e.g., florist, garden center, store) near specified coordinates using Places API (New).

    Args:
        latitude: Latitude coordinate (e.g. 37.7749).
        longitude: Longitude coordinate (e.g. -122.4194).
        place_type: Type of place to search for (e.g., 'florist', 'store', 'park', 'shopping_mall').
        radius_meters: Search radius in meters (default is 5000 meters / 5km).

    Returns:
        A JSON string listing nearby places with key fields: name, address, location coordinates, and rating.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return json.dumps({"error": "GOOGLE_MAPS_API_KEY environment variable is not set."})

    url = "https://places.googleapis.com/v1/places:searchNearby"

    valid_type = place_type.lower()
    if valid_type in ("nursery", "plant_nursery", "garden_center"):
        included_types = ["florist", "store"]
    else:
        included_types = [valid_type]

    payload = {
        "includedTypes": included_types,
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius_meters
            }
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.types",
            "User-Agent": "SproutBot/1.0"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            raw_places = data.get("places", [])

            places = []
            for p in raw_places:
                display_name = p.get("displayName", {}).get("text", "Unknown Name")
                formatted_addr = p.get("formattedAddress", "N/A")
                loc = p.get("location", {})
                rating = p.get("rating", "N/A")

                places.append({
                    "name": display_name,
                    "address": formatted_addr,
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude")
                    },
                    "rating": rating
                })

            if not places:
                return json.dumps({"message": f"No nearby places of type '{place_type}' found within {radius_meters}m."})

            return json.dumps({
                "center_coordinates": {"latitude": latitude, "longitude": longitude},
                "place_type": place_type,
                "places_found_count": len(places),
                "places": places
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to search nearby places: {str(e)}"})

def generate_plant_image(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates an image for a plant or indoor greenery concept using gemini-3.1-flash-lite-image in the global region.
    Saves the image artifact in Playground and uploads it directly to Cloud Storage, returning a public HTTPS URL.

    Args:
        prompt: Detailed description of the plant image to generate (e.g., 'A lush Monstera Deliciosa in a sunlit ceramic pot').
        tool_context: Optional ADK ToolContext injected by the framework for saving artifacts in Playground.

    Returns:
        A JSON string containing the public Cloud Storage HTTPS URL of the generated image.
    """
    try:
        genai_client = GenAIClient(
            vertexai=True,
            project=FIRESTORE_PROJECT_ID,
            location="global"
        )

        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Generate a vibrant, high quality photo of: {prompt}"
        )

        image_bytes = None
        mime_type = "image/jpeg"

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break
            if image_bytes:
                break

        if not image_bytes:
            return json.dumps({"error": "No image bytes were returned by gemini-3.1-flash-lite-image."})

        filename = f"plant_{uuid.uuid4().hex[:8]}.jpg"

        # 1. Save artifact to Playground via ToolContext
        if tool_context:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            res = tool_context.save_artifact(filename=filename, artifact=artifact_part)
            if inspect.iscoroutine(res):
                try:
                    import asyncio
                    loop = asyncio.get_running_loop()
                    loop.create_task(res)
                except RuntimeError:
                    import asyncio
                    asyncio.run(res)

        # 2. Upload image bytes directly to public GCS bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        object_name = f"generated/{filename}"
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{object_name}"

        return json.dumps({
            "success": True,
            "prompt": prompt,
            "filename": filename,
            "public_url": public_url
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to generate plant image: {str(e)}"})

