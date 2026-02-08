# Conversational Shipment Data Extraction (Gemini-powered)

A full-stack web application that uses a conversational AI interface to **collect, normalise, and export structured shipment data** (origin city, destination city, and shipping date) from natural language user input.

The project demonstrates a practical pattern for combining:
- a lightweight chat UI,
- a modern large language model (Google Gemini),
- and deterministic backend processing,
to turn messy human language into clean, machine-readable JSON.

---

## 🚀 What the Project Does

Users interact with a chatbot and describe a shipment in natural language, for example:

> “I’m shipping from London to Sheffield on Saturday 7th Feb 2026.”

The system:
1. Conducts a natural, guided conversation to collect missing details.
2. Uses **Gemini** to extract structured fields from the conversation.
3. Cleans and normalises the data in Python.
4. Outputs a canonical JSON object, ready for downstream processing.

### Final output format
```json
{
  "ship_from_city": "London",
  "ship_to_city": "Sheffield",
  "ship_date": "2026-02-07"
}
