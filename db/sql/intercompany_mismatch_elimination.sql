SELECT counterparty_entity_id,SUM(debit-credit) AS net_balance FROM journal_line WHERE counterparty_entity_id IS NOT NULL GROUP BY counterparty_entity_id;
