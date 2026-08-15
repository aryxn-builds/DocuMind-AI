-- ==========================================================================================
-- TEST: collection_documents RLS isolation
-- NOT LIVE VERIFIED (Supabase MCP is unauthorized)
-- 
-- Expected Behavior:
-- User A collection + User B document -> INSERT rejected
-- User A collection + User A document -> INSERT allowed
-- ==========================================================================================

BEGIN;

-- 1. Setup mock users
-- Assuming user_a_id and user_b_id are valid UUIDs in auth.users
-- In a real pgTAP test, we would mock these or use actual seeded UUIDs.
DO $$
DECLARE
    user_a uuid := '00000000-0000-0000-0000-000000000001';
    user_b uuid := '00000000-0000-0000-0000-000000000002';
    doc_a uuid := gen_random_uuid();
    doc_b uuid := gen_random_uuid();
    col_a uuid := gen_random_uuid();
BEGIN
    -- Create dummy documents
    -- Bypassing RLS by running as superuser for setup
    INSERT INTO public.documents (id, user_id, title, original_filename, file_path, file_type, file_size_bytes)
    VALUES 
        (doc_a, user_a, 'Doc A', 'doc_a.pdf', '/doc_a.pdf', 'pdf', 100),
        (doc_b, user_b, 'Doc B', 'doc_b.pdf', '/doc_b.pdf', 'pdf', 100);

    -- Create a collection for User A
    INSERT INTO public.collections (id, user_id, name)
    VALUES (col_a, user_a, 'Collection A');

    -- 2. Test: User A inserting User A's document (SHOULD SUCCEED)
    -- Impersonate User A
    EXECUTE 'set local role authenticated';
    EXECUTE format('set local request.jwt.claims = ''{"sub": "%s"}''', user_a);

    INSERT INTO public.collection_documents (collection_id, document_id)
    VALUES (col_a, doc_a);
    
    RAISE NOTICE 'SUCCESS: User A inserted User A document into User A collection.';

    -- 3. Test: User A inserting User B's document (SHOULD FAIL)
    BEGIN
        INSERT INTO public.collection_documents (collection_id, document_id)
        VALUES (col_a, doc_b);
        -- If we reach here, the RLS policy failed to block it
        RAISE EXCEPTION 'RLS BYPASS VULNERABILITY: User A successfully inserted User B document!';
    EXCEPTION
        WHEN RLS_POLICY_VIOLATION OR check_violation THEN
            -- Expected behavior (in Supabase RLS, an insert violating WITH CHECK throws an error)
            RAISE NOTICE 'SUCCESS: RLS prevented User A from inserting User B document.';
    END;
END $$;

ROLLBACK;
