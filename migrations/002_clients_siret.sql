-- Add SIRET to clients for reliable client-from-invoice matching
ALTER TABLE clients ADD COLUMN IF NOT EXISTS siret text;
CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_siret_unique
    ON clients(siret) WHERE siret IS NOT NULL;
