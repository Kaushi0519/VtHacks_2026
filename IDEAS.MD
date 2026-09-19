# EXPLORING TRACKS AND IDEAS

Company Specific Tracks:
    - GoDaddy - multi agent systems that discover, verify, and communicate with other agents and services across the open web using ANS.
    - Deloitte x Databricks - Build a data-driven AI agent for a campus career navigator, campus life intelligence hub, or Hokie smart campus.
    - Peraton - Build an AI solution for a mission-critical challenge.
    - Impiricus - building the next hcp engagement tool, Create a working tool or five-minute pitch for a new way to engage healthcare professionals.

General Tracks:
    - Best DEI Hack - implement diversity, equity & inclusion features (used as a lens across our build, not a separate project)


Strategy:
    - Pick ONE company track as the spine, use DEI as a lens layered on top.
    - can create a vt related program that relates to databricks track
    - can branch on top of that with GoDaddy related agents that fetch real data or anything over the web


Ideas:
    - CourseForum for Vtech
        - aligns with databricks track (campus data-driven agent)
        - can easily implement DEI Features
        - can use GoDaddy aligned agents across the web to fetch and pull real data to feed into "TheCourseForum"

    - Combination of GoDaddy, Databricks, and Peraton. Build a trusted multi agent campus response Concept: Specialized agents for facilities, campus safety, energy, and space management. They detect anomalies in operations data, like a temperature spike, an unusual energy draw, or an overcrowded building, then coordinate a response and propose an action.
GoDaddy ANS: Every agent has a verifiable, domain-anchored identity. Agents only act on messages from verified peers, and you show an impostor agent trying to inject a fake "evacuate Goodwin" alert and getting rejected. This is a real use of ANS, not just a mention.
Peraton, mission-critical AI: The stakes are real (safety alerts), so add guardrails, a human-approval step for high-severity actions, an audit log, and graceful failure when data is missing. Judges should see that you designed for trust.
Deloitte/Databricks: Put the data layer on Databricks (sensor, work-order, and energy tables, plus governance) and present it consultant-style. Their rubric rewards realism, a deployment roadmap and future enhancements, and strong Q&A, so build a short "pilot at VT, then scale" slide.
Demo flow: A live anomaly appears, the agents verify each other and coordinate, an impostor is blocked, and the dashboard shows a recommended action with estimated savings or risk reduction.
Split for 4 people:
Agent orchestration and ANS integration
Data pipeline and Databricks
Dashboard and UI
Pitch, roadmap, and Deloitte-style narrative
