# Intelligent Query Handling Decision Tree

## Objective
Design a theoretical, high-impact triage logic for Hobart that:
- auto-resolves simple, objective requests,
- routes non-simple requests to the right human desk or workflow,
- reduces desk ping-pong and response latency.

## Visual Decision Tree

```mermaid
flowchart TD
    A["Incoming Query (SR)"] --> B{"Is answer directly available in trusted data<br/>with no subjective interpretation?"}

    B -- Yes --> C["AI Response"]
    C --> C3{"Client satisfied?"}
    C3 -- Yes --> C4["Close or monitor ticket"]
    C3 -- No --> F["Suggest best-fit human agent based on expertise, load, and SLA risk"]

    B -- No --> D{"Does this require multiple desks?"}

    D -- No --> F["Suggest best-fit human agent based on expertise, load, and SLA risk"]
    D -- Yes --> E["AI Coordinator: Multi-Desk Workflow Orchestrator"]
    E --> E1["Assign human ticket owner (accountable end-to-end)"]
    E1 --> E2["Create parallel desk tasks + dependency tracking"]
    E2 --> E3["Consolidate outputs + final client response"]

    F --> F2["Human agent handles case"]

    C4 --> G["Outcome Tracking"]
    E3 --> G
    F2 --> G
    G --> H["KPI reporting and governance"]
```

## Node Logic (Plain Language)

1. Data-Objective Gate
- Question: can the request be answered with factual system data only?
- If yes, AI can answer directly.
- If no, move to workflow routing.

2. AI Response
- Handles repetitive, low-risk requests (status check, due date, known process step).
- If the client is not satisfied, the case is redirected to a human agent flow.

3. Multi-Desk Decision
- If resolution requires several desks, an AI coordinator orchestrates the workflow instead of serial handoffs.
- A human ticket owner remains accountable end-to-end for decisions and client communication.

4. Single-Desk Smart Routing
- If one desk can solve it, suggest the most relevant available human agent.
- Relevance should combine skill fit, active workload, and SLA pressure.

5. Feedback Loop
- Every handled case updates performance logs.
- Logs support KPI reporting, governance, and decision accountability.

## Practical Rules (Theoretical Policy Layer)

```text
Rule 1: If objective data answer exists, AI responds.
Rule 2: If the client is not satisfied with AI response, route to a human agent.
Rule 3: If more than one desk is required, AI orchestrates parallel desk tasks while one human owner stays accountable for the ticket.
Rule 4: If one desk is required, route to best-fit non-overloaded human agent.
Rule 5: Log all decisions for auditability and model improvement.
```

## Why This Stands Out in a Management Pitch
- It is not "AI replaces agents"; it is "AI protects agent time for complex work."
- It directly targets known friction points: looping, misrouting, and slow responses.
- It is actionable: each branch maps to a clear operating model and KPI ownership.
