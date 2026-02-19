# Reopen Rate 2024 vs 2025

## Objectif
Comparer le taux de tickets reouverts entre 2024 et 2025 pour evaluer la qualite de reponse Hobart.

## Definition KPI
- Population: tickets fermes (`closingdate_parsed` non nul).
- Ticket reouvert: `reopen_date_parsed` non nul.
- Taux de reouverture = `reopened_tickets / closed_tickets`.

## Guardrail Data
Pour eviter un biais de nullite sur le champ `reopen_date_parsed`, l'analyse est restreinte au load period **2025-01_to_2025-09** (zone ou le signal de reopen est renseigne).

## Resultats

|   creation_year | closed_tickets   | reopened_tickets   | reopen_rate_pct   |
|----------------:|:-----------------|:-------------------|:------------------|
|            2024 | 2,186,555        | 1,808              | 0.0827%           |
|            2025 | 2,008,415        | 1,210              | 0.0602%           |

## Comparaison 2025 vs 2024
- Difference absolue: **-0.0224 points**
- Variation relative: **-27.14%**
