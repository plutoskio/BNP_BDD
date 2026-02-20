BEGIN TRANSACTION;

-- 1) New intents for newly created desks (IADV, TAX, IT)
INSERT OR IGNORE INTO intents (intent_code, intent_name) VALUES
  ('investment_advice_request', 'Investment Advice Request'),
  ('portfolio_rebalancing_advice', 'Portfolio Rebalancing Advice'),
  ('risk_profile_review', 'Risk Profile Review'),
  ('tax_withholding_query', 'Tax Withholding Query'),
  ('tax_document_request', 'Tax Document Request'),
  ('capital_gains_tax_query', 'Capital Gains Tax Query'),
  ('platform_access_issue', 'Platform Access Issue'),
  ('password_reset_request', 'Password Reset Request'),
  ('api_connectivity_issue', 'API Connectivity Issue');

-- 2) Routing rules for new intents
INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires human investment advisory review and follow-up.'
FROM intents i
JOIN desks d ON d.desk_code = 'IADV'
WHERE i.intent_code = 'investment_advice_request'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires portfolio advisory analysis by investment desk.'
FROM intents i
JOIN desks d ON d.desk_code = 'IADV'
WHERE i.intent_code = 'portfolio_rebalancing_advice'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires suitability and risk-profile review by investment desk.'
FROM intents i
JOIN desks d ON d.desk_code = 'IADV'
WHERE i.intent_code = 'risk_profile_review'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires tax specialist review of withholding treatment.'
FROM intents i
JOIN desks d ON d.desk_code = 'TAX'
WHERE i.intent_code = 'tax_withholding_query'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires tax operations handling for statement/document request.'
FROM intents i
JOIN desks d ON d.desk_code = 'TAX'
WHERE i.intent_code = 'tax_document_request'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires tax specialist review for capital gains treatment.'
FROM intents i
JOIN desks d ON d.desk_code = 'TAX'
WHERE i.intent_code = 'capital_gains_tax_query'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires IT support intervention for platform access issue.'
FROM intents i
JOIN desks d ON d.desk_code = 'IT'
WHERE i.intent_code = 'platform_access_issue'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires IT support intervention for credential reset and account unlock.'
FROM intents i
JOIN desks d ON d.desk_code = 'IT'
WHERE i.intent_code = 'password_reset_request'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

INSERT INTO routing_rules (intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template)
SELECT i.intent_id, 0, 0, d.desk_id,
       'Requires IT diagnostics for API/integration connectivity issue.'
FROM intents i
JOIN desks d ON d.desk_code = 'IT'
WHERE i.intent_code = 'api_connectivity_issue'
  AND NOT EXISTS (SELECT 1 FROM routing_rules rr WHERE rr.intent_id = i.intent_id);

-- 3) Active agents for newly created desks so routing remains desk-consistent.
WITH new_agents(agent_code, full_name, email, desk_code, max_open_tickets, created_at) AS (
  VALUES
    ('AGT0029', 'Taylor Beaumont', 'agt0029@mvp.demo', 'IADV', 20, '2026-02-19 22:40:00'),
    ('AGT0030', 'Quinn Mercer',    'agt0030@mvp.demo', 'IADV', 18, '2026-02-19 22:40:00'),
    ('AGT0031', 'Drew Sinclair',   'agt0031@mvp.demo', 'IADV', 22, '2026-02-19 22:40:00'),

    ('AGT0032', 'Casey Laurent',   'agt0032@mvp.demo', 'TAX',  21, '2026-02-19 22:40:00'),
    ('AGT0033', 'Avery Dubois',    'agt0033@mvp.demo', 'TAX',  19, '2026-02-19 22:40:00'),
    ('AGT0034', 'Noah Pelletier',  'agt0034@mvp.demo', 'TAX',  20, '2026-02-19 22:40:00'),

    ('AGT0035', 'Jordan Renaud',   'agt0035@mvp.demo', 'IT',   24, '2026-02-19 22:40:00'),
    ('AGT0036', 'Morgan Tellier',  'agt0036@mvp.demo', 'IT',   26, '2026-02-19 22:40:00'),
    ('AGT0037', 'Parker Vigneault','agt0037@mvp.demo', 'IT',   22, '2026-02-19 22:40:00')
)
INSERT INTO agents (
  agent_code,
  full_name,
  email,
  desk_id,
  is_active,
  max_open_tickets,
  created_at
)
SELECT
  na.agent_code,
  na.full_name,
  na.email,
  d.desk_id,
  1,
  na.max_open_tickets,
  na.created_at
FROM new_agents na
JOIN desks d ON d.desk_code = na.desk_code
WHERE NOT EXISTS (
  SELECT 1
  FROM agents a
  WHERE a.agent_code = na.agent_code OR a.email = na.email
);

COMMIT;
