BEGIN TRANSACTION;

-- Add extra cash accounts for demo personas where needed.
WITH new_accounts(client_code, account_number, currency, cash_balance, available_cash, held_cash, updated_at) AS (
  VALUES
    ('CL0001', 'ACCT-CL0001-EUR-01', 'EUR', 485000.00, 450000.00, 35000.00, '2026-02-19 09:00:00'),
    ('CL0003', 'ACCT-CL0003-USD-01', 'USD', 720000.00, 700000.00, 20000.00, '2026-02-19 09:00:00'),
    ('CL0004', 'ACCT-CL0004-CHF-01', 'CHF', 390000.00, 360000.00, 30000.00, '2026-02-19 09:00:00')
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

-- Add curated, easy-to-test trades per persona.
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
    ('CL0001','TRD910101','AAPL','BUY', 1200.00, 191.2500,'EXECUTED',NULL,'2026-02-17 09:10:00','2026-02-17 09:20:00','2026-02-17 14:35:00','2026-02-19 14:35:00'),
    ('CL0001','TRD910102','MSFT','SELL',  650.00, 413.1000,'CONFIRMED',NULL,'2026-02-17 10:05:00','2026-02-17 10:20:00',NULL,'2026-02-20 10:20:00'),
    ('CL0001','TRD910103','SPY','BUY',    900.00, 502.4000,'PENDING',NULL,'2026-02-17 11:15:00',NULL,NULL,'2026-02-21 11:15:00'),
    ('CL0001','TRD910104','EURUSD','SELL',180000.00,1.0823,'FAILED','Insufficient settlement cash','2026-02-17 12:00:00',NULL,NULL,'2026-02-21 12:00:00'),

    ('CL0002','TRD910201','NVDA','BUY',    500.00, 781.4500,'EXECUTED',NULL,'2026-02-17 09:00:00','2026-02-17 09:12:00','2026-02-17 13:40:00','2026-02-19 13:40:00'),
    ('CL0002','TRD910202','QQQ','SELL',    420.00, 429.8000,'CONFIRMED',NULL,'2026-02-17 10:10:00','2026-02-17 10:22:00',NULL,'2026-02-20 10:22:00'),
    ('CL0002','TRD910203','JPM','BUY',    1200.00, 181.3500,'EXECUTED',NULL,'2026-02-17 11:05:00','2026-02-17 11:17:00','2026-02-17 15:10:00','2026-02-19 15:10:00'),
    ('CL0002','TRD910204','USDJPY','SELL',250000.00,149.6200,'CANCELLED',NULL,'2026-02-17 11:50:00','2026-02-17 12:03:00',NULL,'2026-02-21 12:03:00'),

    ('CL0003','TRD910301','META','BUY',    700.00, 438.9000,'EXECUTED',NULL,'2026-02-17 09:30:00','2026-02-17 09:45:00','2026-02-17 14:10:00','2026-02-19 14:10:00'),
    ('CL0003','TRD910302','TLT','BUY',    1500.00,  93.4200,'CONFIRMED',NULL,'2026-02-17 10:40:00','2026-02-17 10:55:00',NULL,'2026-02-20 10:55:00'),
    ('CL0003','TRD910303','GBPUSD','SELL',220000.00,1.2678,'PENDING',NULL,'2026-02-17 11:20:00',NULL,NULL,'2026-02-21 11:20:00'),
    ('CL0003','TRD910304','XOM','SELL',   1800.00, 102.1500,'FAILED','Compliance hold','2026-02-17 12:05:00',NULL,NULL,'2026-02-21 12:05:00'),

    ('CL0004','TRD910401','GOOGL','BUY',   380.00, 188.4500,'EXECUTED',NULL,'2026-02-17 09:05:00','2026-02-17 09:18:00','2026-02-17 13:25:00','2026-02-19 13:25:00'),
    ('CL0004','TRD910402','AMZN','SELL',   520.00, 171.8200,'CONFIRMED',NULL,'2026-02-17 10:25:00','2026-02-17 10:38:00',NULL,'2026-02-20 10:38:00'),
    ('CL0004','TRD910403','US10Y','BUY',   900.00, 108.3000,'PENDING',NULL,'2026-02-17 11:30:00',NULL,NULL,'2026-02-21 11:30:00'),
    ('CL0004','TRD910404','USDCHF','SELL',200000.00,0.8742,'CANCELLED',NULL,'2026-02-17 12:20:00',NULL,NULL,'2026-02-21 12:20:00'),

    ('CL0005','TRD910501','SPY','BUY',    1100.00, 503.1000,'EXECUTED',NULL,'2026-02-17 09:15:00','2026-02-17 09:29:00','2026-02-17 14:00:00','2026-02-19 14:00:00'),
    ('CL0005','TRD910502','BND','BUY',    3000.00,  72.4500,'CONFIRMED',NULL,'2026-02-17 10:15:00','2026-02-17 10:28:00',NULL,'2026-02-20 10:28:00'),
    ('CL0005','TRD910503','FR10Y','SELL', 1300.00, 109.2500,'PENDING',NULL,'2026-02-17 11:10:00',NULL,NULL,'2026-02-21 11:10:00'),
    ('CL0005','TRD910504','DE10Y','SELL', 1400.00, 116.1000,'FAILED','Counterparty reject','2026-02-17 12:10:00',NULL,NULL,'2026-02-21 12:10:00')
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
    WHERE p.client_id = c.client_id AND p.symbol = nt.symbol
    ORDER BY p.position_id
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
