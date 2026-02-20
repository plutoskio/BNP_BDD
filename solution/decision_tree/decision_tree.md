# Intelligent Query Handling Decision Tree

## Objective
Design a theoretical, high-impact triage logic for Hobart that:
- auto-resolves simple, objective requests,
- routes non-simple requests to the right human desk or workflow,
- reduces desk ping-pong and response latency.

## Visual Decision Tree

```mermaid
flowchart LR
    A["New SR"] --> B{"Objective data answer?"}

    B -- Yes --> C["AI reply"]
    C --> D{"Client satisfied?"}
    D -- Yes --> E["Close / Monitor"]
    D -- No --> H["Smart route to agent<br/>(based on topic and workload)"]

    B -- No --> F{"Multi-desk case?"}
    F -- No --> H
    F -- Yes --> G["AI coordinator"]
    G --> G1["Assign single owner"]
    G1 --> G2["Run desk tasks in parallel"]
    G2 --> G3["Merge outputs + final response"]

    H --> I["Human resolution"]

    E --> J["Outcome log"]
    G3 --> J
    I --> J
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
