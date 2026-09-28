# My agent: SproutBot (Smart Plant Care & Nursery Assistant)

One-liner: A conversational agent that helps plant enthusiasts care for their indoor plant collection with personalized watering schedules, care diagnostics, rich catalog cards, and generated plant visuals.

## Tool Coverage

- **Memory**: Remembers your home plant collection, room lighting conditions (e.g., south-facing window, low light), watering history, and experience level.
- **Tools**: 
  - `lookup_plant_care(species)`: Fetches care instructions, light requirements, and ideal temperature range.
  - `log_watering(plant_id)`: Records watering events and computes next due date.
  - `diagnose_plant_issue(symptom)`: Looks up care issues (e.g., yellowing leaves, root rot symptoms) and returns treatment steps.
- **Catalog / UI**: Plant inventory catalog (rendered as rich A2UI cards displaying care stats, watering status badges, and plant profiles).
- **Image Generation**: Generates visual previews of mature healthy plants, ideal room placement layouts, or foliage health references.
- **Sandbox**: Computes customized watering schedule adjustments dynamically using temperature, humidity, and pot size metrics.

---
**Recommended for every project**: Memory, Firestore storage, function tools, image generation, A2UI cards.  
**Agent-specific / stretch**: Code sandbox for environmental schedule math, Imagen for plant visuals, Firestore for plant catalog persistence.
