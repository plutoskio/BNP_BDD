# Demo Personas Reference (Email Routing MVP)

This file lists test-ready client personas mapped in `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db`.

## Persona Mapping
- Robin: `rmarlier@albertschool.com` (`CL0001`)
- Alexandre: `adelattre@albertschool.com` (`CL0002`)
- Milo: `mcardona@albertschool.com` (`CL0003`)
- Jean: `jleclerc@albertschool.com` (`CL0004`)
- Matheo: `mvicente@albertschool.com` (`CL0005`)
- Suzana: `suzana.tadic@bnpparibas.com` (`CL0101`)
- William: `william.aumont@bnpparibas.com` (`CL0102`)

## Curated Trade Refs (safe for direct automated reply)
- Robin (`CL0001`): `TRD910101`, `TRD910102`, `TRD910103`, `TRD910104`
- Alexandre (`CL0002`): `TRD910201`, `TRD910202`, `TRD910203`, `TRD910204`
- Milo (`CL0003`): `TRD910301`, `TRD910302`, `TRD910303`, `TRD910304`
- Jean (`CL0004`): `TRD910401`, `TRD910402`, `TRD910403`, `TRD910404`
- Matheo (`CL0005`): `TRD910501`, `TRD910502`, `TRD910503`, `TRD910504`
- Suzana (`CL0101`): `TRD910601`, `TRD910602`, `TRD910603`, `TRD910604`
- William (`CL0102`): `TRD910701`, `TRD910702`, `TRD910703`, `TRD910704`

## Example Test Email
- Subject: `Trade status check TRD910501`
- Body:
  `Please confirm the status and execution timestamp for trade TRD910501.`

## Notes
- Trade lookup is owner-scoped: sender email must match the trade's client owner.
- If sender/trade ownership does not match, routing falls back to human review.
