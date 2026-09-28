from google.cloud import firestore

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-41fd6d52d172"

SEEDED_PLANTS = [
    {
        "id": "monstera_01",
        "common_name": "Monstera Deliciosa",
        "species": "Monstera deliciosa",
        "care_level": "Easy",
        "light_requirement": "Bright Indirect Light",
        "water_interval_days": 7,
        "last_watered": "2026-09-21",
        "health_status": "Healthy",
        "notes": "Loves high humidity. Wipe leaves with a damp cloth to clean dust.",
    },
    {
        "id": "fiddle_leaf_01",
        "common_name": "Fiddle Leaf Fig",
        "species": "Ficus lyrata",
        "care_level": "Moderate",
        "light_requirement": "Bright Indirect Light",
        "water_interval_days": 10,
        "last_watered": "2026-09-15",
        "health_status": "Needs Care",
        "notes": "Sensitive to drafts and sudden changes in position. Allow top 2 inches of soil to dry out.",
    },
    {
        "id": "snake_plant_01",
        "common_name": "Snake Plant",
        "species": "Dracaena trifasciata",
        "care_level": "Easy",
        "light_requirement": "Low Light to Bright Light",
        "water_interval_days": 14,
        "last_watered": "2026-09-14",
        "health_status": "Healthy",
        "notes": "Thrives on neglect. Very drought tolerant; avoid overwatering to prevent root rot.",
    },
    {
        "id": "pothos_01",
        "common_name": "Golden Pothos",
        "species": "Epipremnum aureum",
        "care_level": "Easy",
        "light_requirement": "Low to Moderate Indirect Light",
        "water_interval_days": 7,
        "last_watered": "2026-09-22",
        "health_status": "Healthy",
        "notes": "Fast growing trailing vine. Easy to propagate in water.",
    },
]

def seed_firestore():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT_ID}...")
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    collection_ref = db.collection("plants")

    for plant in SEEDED_PLANTS:
        doc_id = plant["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(plant)
        print(f"Seeded plant: {plant['common_name']} ({doc_id})")

    print("\n✅ Firestore seeding completed successfully!")

if __name__ == "__main__":
    seed_firestore()
