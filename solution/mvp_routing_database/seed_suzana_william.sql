BEGIN TRANSACTION;

-- Add two operational client personas so their sender emails are recognized by routing.
WITH new_clients(
  client_code,
  client_name,
  email,
  segment,
  primary_desk_id,
  created_at
) AS (
  VALUES
    ('CL0101', 'Suzana Tadic', 'suzana.tadic@bnpparibas.com', 'PrivateBanking', 1, '2026-02-20 10:00:00'),
    ('CL0102', 'William Aumont', 'william.aumont@bnpparibas.com', 'PrivateBanking', 1, '2026-02-20 10:00:00')
)
INSERT INTO clients (
  client_code,
  client_name,
  email,
  segment,
  primary_desk_id,
  created_at
)
SELECT
  nc.client_code,
  nc.client_name,
  nc.email,
  nc.segment,
  nc.primary_desk_id,
  nc.created_at
FROM new_clients nc
WHERE NOT EXISTS (
  SELECT 1
  FROM clients c
  WHERE c.client_code = nc.client_code OR lower(c.email) = lower(nc.email)
);

-- Add cash accounts for operational cash-related requests.
WITH new_accounts(
  client_code,
  account_number,
  currency,
  cash_balance,
  available_cash,
  held_cash,
  updated_at
) AS (
  VALUES
    ('CL0101', 'ACCT-CL0101-EUR-01', 'EUR', 650000.00, 620000.00, 30000.00, '2026-02-20 10:05:00'),
    ('CL0101', 'ACCT-CL0101-USD-01', 'USD', 420000.00, 390000.00, 30000.00, '2026-02-20 10:05:00'),
    ('CL0102', 'ACCT-CL0102-EUR-01', 'EUR', 730000.00, 700000.00, 30000.00, '2026-02-20 10:05:00'),
    ('CL0102', 'ACCT-CL0102-GBP-01', 'GBP', 360000.00, 335000.00, 25000.00, '2026-02-20 10:05:00')
)
INSERT INTO cash_accounts (
  account_number,
  client_id,
  currency,
  cash_balance,
  available_cash,
  held_cash,
  updated_at
)
SELECT
  na.account_number,
  c.client_id,
  na.currency,
  na.cash_balance,
  na.available_cash,
  na.held_cash,
  na.updated_at
FROM new_accounts na
JOIN clients c ON c.client_code = na.client_code
WHERE NOT EXISTS (
  SELECT 1 FROM cash_accounts ca WHERE ca.account_number = na.account_number
);

-- Add positions so portfolio and holdings requests return data.
WITH new_positions(
  client_code,
  symbol,
  asset_class,
  quantity,
  avg_cost,
  market_price,
  as_of_date
) AS (
  VALUES
    ('CL0101', 'AAPL', 'EQUITY', 1450.00, 176.20, 191.10, '2026-02-20 09:55:00'),
    ('CL0101', 'US10Y', 'BOND',   980.00, 106.40, 108.15, '2026-02-20 09:55:00'),
    ('CL0102', 'MSFT', 'EQUITY', 1100.00, 401.80, 413.25, '2026-02-20 09:55:00'),
    ('CL0102', 'BND',  'ETF',    3200.00,  71.95,  72.40, '2026-02-20 09:55:00')
)
INSERT INTO positions (
  client_id,
  symbol,
  asset_class,
  quantity,
  avg_cost,
  market_price,
  market_value,
  as_of_date
)
SELECT
  c.client_id,
  np.symbol,
  np.asset_class,
  np.quantity,
  np.avg_cost,
  np.market_price,
  ROUND(np.quantity * np.market_price, 2) AS market_value,
  np.as_of_date
FROM new_positions np
JOIN clients c ON c.client_code = np.client_code
WHERE NOT EXISTS (
  SELECT 1
  FROM positions p
  WHERE p.client_id = c.client_id
    AND p.symbol = np.symbol
    AND p.as_of_date = np.as_of_date
);

-- Add curated trade refs for direct "trade status" email tests, like Jean.
WITH new_trades(
  client_code,
  trade_ref,
  symbol,
  side,
  quantity,
  price,
  trade_status,
  fail_reason,
  submitted_at,
  confirmed_at,
  executed_at,
  settlement_date
) AS (
  VALUES
    ('CL0101','TRD910601','AAPL','BUY',   420.00,191.10,'EXECUTED',NULL,'2026-02-20 09:12:00','2026-02-20 09:20:00','2026-02-20 13:42:00','2026-02-24 13:42:00'),
    ('CL0101','TRD910602','US10Y','SELL', 700.00,108.05,'CONFIRMED',NULL,'2026-02-20 10:05:00','2026-02-20 10:16:00',NULL,'2026-02-25 10:16:00'),
    ('CL0101','TRD910603','EURUSD','BUY',150000.00,1.0842,'PENDING',NULL,'2026-02-20 11:10:00',NULL,NULL,'2026-02-26 11:10:00'),
    ('CL0101','TRD910604','SPY','SELL',   300.00,504.80,'FAILED','Compliance validation pending','2026-02-20 12:00:00',NULL,NULL,'2026-02-26 12:00:00'),

    ('CL0102','TRD910701','MSFT','BUY',   390.00,413.25,'EXECUTED',NULL,'2026-02-20 09:22:00','2026-02-20 09:30:00','2026-02-20 14:05:00','2026-02-24 14:05:00'),
    ('CL0102','TRD910702','BND','SELL',  1200.00, 72.40,'CONFIRMED',NULL,'2026-02-20 10:18:00','2026-02-20 10:30:00',NULL,'2026-02-25 10:30:00'),
    ('CL0102','TRD910703','GBPUSD','SELL',180000.00,1.2691,'PENDING',NULL,'2026-02-20 11:20:00',NULL,NULL,'2026-02-26 11:20:00'),
    ('CL0102','TRD910704','NVDA','BUY',   210.00,789.40,'CANCELLED',NULL,'2026-02-20 12:12:00',NULL,NULL,'2026-02-26 12:12:00')
)
INSERT INTO trades (
  trade_ref,
  client_id,
  position_id,
  symbol,
  side,
  quantity,
  price,
  notional,
  trade_status,
  fail_reason,
  submitted_at,
  confirmed_at,
  executed_at,
  settlement_date
)
SELECT
  nt.trade_ref,
  c.client_id,
  (
    SELECT p.position_id
    FROM positions p
    WHERE p.client_id = c.client_id
      AND p.symbol = nt.symbol
    ORDER BY p.as_of_date DESC, p.position_id DESC
    LIMIT 1
  ) AS position_id,
  nt.symbol,
  nt.side,
  nt.quantity,
  nt.price,
  ROUND(nt.quantity * nt.price, 2) AS notional,
  nt.trade_status,
  nt.fail_reason,
  nt.submitted_at,
  nt.confirmed_at,
  nt.executed_at,
  nt.settlement_date
FROM new_trades nt
JOIN clients c ON c.client_code = nt.client_code
WHERE NOT EXISTS (
  SELECT 1 FROM trades t WHERE t.trade_ref = nt.trade_ref
);

COMMIT;
