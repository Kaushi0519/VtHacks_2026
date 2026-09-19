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


========================================
CHOSEN DIRECTION: HokieBridge
========================================
Tracks: GoDaddy + Deloitte x Databricks + Best DEI Hack (+ Peraton as stretch)

One-liner:
    A student describes their situation in plain language ("I might lose my meal
    plan and can't afford next semester"), and a mesh of verified specialist agents
    finds the real campus + web resources they qualify for, translates bureaucratic
    requirements into plain steps, and does it anonymously.

Why each track is satisfied:

    GoDaddy / ANS (technical centerpiece):
        - Each resource domain is a separate agent with a verifiable, domain-anchored
          ANS identity: FinancialAidAgent, DisabilityServicesAgent, FoodSecurityAgent,
          HousingAgent, MentalHealthAgent.
        - A Navigator agent discovers and verifies peers via ANS, then routes the
          student's need to the right specialists.
        - KILLER DEMO: a predatory "ScholarshipAgent" (really a phishing scam
          harvesting SSNs) tries to inject a response and gets REJECTED because it
          lacks a verified ANS identity. Real ANS usage, not a mention - and a genuine
          DEI issue since financial scams disproportionately target first-gen and
          low-income students.

    Deloitte x Databricks:
        - Databricks is the data layer: resource catalog, eligibility rules, deadlines,
          with governance/lineage.
        - A matching model ranks resources by eligibility fit.
        - Present consultant-style: "pilot at VT -> scale to any campus" roadmap.

    Best DEI Hack (the mission):
        - Serves first-gen, low-income, disabled, transfer, international, and
          undocumented students.
        - Accessibility-first UI (screen-reader, WCAG, keyboard nav), anonymous by
          default, plain-language translation of bureaucratic jargon.

    Peraton (stretch -> makes it 4 tracks):
        - Crisis path: if the navigator detects distress language, a mission-critical
          guardrail escalates with a human-in-the-loop handoff to counseling + an
          audit log + graceful failure when data is missing.

Demo flow (90 seconds):
    1. Student types their situation -> Navigator parses it
    2. Routes to FoodSecurity + FinancialAid agents (discovered & ANS-verified)
    3. Agents query Databricks -> return matched resources + deadlines + plain steps
    4. Phishing "scholarship" impostor tries to respond -> ANS blocks it (show it)
    5. Distress language triggers -> crisis escalation to human handoff + audit log
    6. Toggle accessibility / anonymous mode to close

4-person split:
    1. Agents + ANS      - identity, discovery, verification, impostor rejection
    2. Databricks        - resource catalog, eligibility data, governance, matching
    3. Frontend/UX       - accessibility-first chat, anonymous mode, "blocked scam" visual
    4. Pitch + Peraton   - guardrails, audit log, crisis path, DEI narrative, demo script

Open decisions:
    - Name: HokieBridge (placeholder) - confirm or change
    - Scope: commit to Peraton crisis-path (4 tracks, more work) vs. keep as
      "future enhancement" slide (3 tracks, safer)
