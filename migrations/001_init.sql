-- Ledgerly schema — full init
-- Run in Supabase SQL Editor

-- Enable uuid generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- clients
CREATE TABLE IF NOT EXISTS clients (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code text UNIQUE NOT NULL,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- suppliers
CREATE TABLE IF NOT EXISTS suppliers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name text NOT NULL,
    name_normalized text UNIQUE NOT NULL,
    siret text UNIQUE,
    default_compte text,
    default_dossier_client_id uuid REFERENCES clients(id),
    default_journal text NOT NULL DEFAULT 'HA',
    invoices_count int NOT NULL DEFAULT 0,
    last_seen timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- invoices
CREATE TABLE IF NOT EXISTS invoices (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    state text NOT NULL DEFAULT 'pending',
    state_reason text,

    uploaded_at timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz,
    pdf_storage_path text,
    pdf_original_name text,

    supplier_id uuid REFERENCES suppliers(id),
    supplier_name_raw text,
    siret text,
    invoice_date date,
    invoice_number text,
    amount_ht numeric(12,2),
    amount_tva numeric(12,2),
    amount_ttc numeric(12,2),
    tva_rate numeric(5,2),

    compte text,
    dossier_client_id uuid REFERENCES clients(id),
    journal text NOT NULL DEFAULT 'HA',
    libelle text,
    observation text,

    classification text,
    duplicate_of uuid REFERENCES invoices(id),
    raw_extraction jsonb
);

CREATE INDEX IF NOT EXISTS idx_invoices_state ON invoices(state);
CREATE INDEX IF NOT EXISTS idx_invoices_supplier_id ON invoices(supplier_id);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_date ON invoices(invoice_date);

-- recap_failures
CREATE TABLE IF NOT EXISTS recap_failures (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    failed_at timestamptz NOT NULL DEFAULT now(),
    error text
);

-- RPC: validate_invoice
-- Atomic transaction: update invoice + upsert supplier defaults + bump counter
CREATE OR REPLACE FUNCTION validate_invoice(
    p_invoice_id uuid,
    p_compte text,
    p_dossier_client_id uuid,
    p_journal text,
    p_libelle text,
    p_invoice_date date,
    p_invoice_number text,
    p_amount_ht numeric,
    p_amount_tva numeric,
    p_amount_ttc numeric,
    p_tva_rate numeric,
    p_supplier_name text,
    p_supplier_name_normalized text,
    p_siret text DEFAULT NULL
) RETURNS void AS $$
DECLARE
    v_supplier_id uuid;
BEGIN
    -- Find or create supplier
    SELECT id INTO v_supplier_id
    FROM suppliers
    WHERE (p_siret IS NOT NULL AND siret = p_siret)
       OR name_normalized = p_supplier_name_normalized
    LIMIT 1;

    IF v_supplier_id IS NULL THEN
        INSERT INTO suppliers (name, name_normalized, siret, default_compte, default_dossier_client_id, default_journal, invoices_count, last_seen)
        VALUES (p_supplier_name, p_supplier_name_normalized, p_siret, p_compte, p_dossier_client_id, p_journal, 1, now())
        RETURNING id INTO v_supplier_id;
    ELSE
        UPDATE suppliers
        SET default_compte = p_compte,
            default_dossier_client_id = p_dossier_client_id,
            default_journal = p_journal,
            invoices_count = invoices_count + 1,
            last_seen = now()
        WHERE id = v_supplier_id;
    END IF;

    -- Update invoice
    UPDATE invoices
    SET state = 'done',
        classification = 'manual',
        state_reason = NULL,
        processed_at = now(),
        supplier_id = v_supplier_id,
        compte = p_compte,
        dossier_client_id = p_dossier_client_id,
        journal = p_journal,
        libelle = p_libelle,
        invoice_date = p_invoice_date,
        invoice_number = p_invoice_number,
        amount_ht = p_amount_ht,
        amount_tva = p_amount_tva,
        amount_ttc = p_amount_ttc,
        tva_rate = p_tva_rate
    WHERE id = p_invoice_id;
END;
$$ LANGUAGE plpgsql;
