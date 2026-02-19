from __future__ import annotations

from fastapi import FastAPI, HTTPException

from mvp_agent import InboundMessage, RoutingOutput, RoutingService, load_settings


settings = load_settings()
service = RoutingService(settings)

app = FastAPI(title="OpenAI Agents Routing MVP", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/inbound", response_model=RoutingOutput)
def inbound(payload: InboundMessage) -> RoutingOutput:
    return service.process_inbound(payload)


@app.get("/ticket/{ticket_ref}")
def ticket_status(ticket_ref: str) -> dict:
    snapshot = service.get_ticket_status(ticket_ref)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="ticket_not_found")
    return snapshot
