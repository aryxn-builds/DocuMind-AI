-- =============================================================================
-- DocuMind AI — Migration: Storage RLS
-- Phase 7: Document Upload + Private Storage Architecture
-- =============================================================================
-- Creates the private 'documents' bucket and enforces row-level security
-- on storage.objects so that users can only access their own files.
--
-- Path convention: {user_id}/{document_id}/{sanitized_filename}
-- The first path segment is always the user's UUID, enabling a simple
-- prefix-based ownership check without any join against public.documents.
-- =============================================================================

-- Create the private documents bucket (idempotent via DO block).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM storage.buckets WHERE id = 'documents'
  ) THEN
    INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
    VALUES (
      'documents',
      'documents',
      false,  -- PRIVATE: no direct public URL access
      26214400,  -- 25 MB in bytes (25 * 1024 * 1024)
      ARRAY[
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/png',
        'image/jpeg'
      ]
    );
  END IF;
END $$;

-- =============================================================================
-- Storage RLS Policies
-- These operate on storage.objects for bucket 'documents'.
-- The first path segment (foldername index 1) must equal the authenticated
-- user's UUID, ensuring strict per-user isolation.
-- =============================================================================

-- Policy 1: INSERT — users can only upload to their own folder.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname = 'documind_documents_insert_own_folder'
  ) THEN
    EXECUTE $policy$
      CREATE POLICY documind_documents_insert_own_folder
        ON storage.objects
        FOR INSERT
        WITH CHECK (
          bucket_id = 'documents'
          AND (storage.foldername(name))[1] = auth.uid()::text
        );
    $policy$;
  END IF;
END $$;

-- Policy 2: SELECT — users can only read files in their own folder.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname = 'documind_documents_select_own_folder'
  ) THEN
    EXECUTE $policy$
      CREATE POLICY documind_documents_select_own_folder
        ON storage.objects
        FOR SELECT
        USING (
          bucket_id = 'documents'
          AND (storage.foldername(name))[1] = auth.uid()::text
        );
    $policy$;
  END IF;
END $$;

-- Policy 3: DELETE — users can only delete files in their own folder.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname = 'documind_documents_delete_own_folder'
  ) THEN
    EXECUTE $policy$
      CREATE POLICY documind_documents_delete_own_folder
        ON storage.objects
        FOR DELETE
        USING (
          bucket_id = 'documents'
          AND (storage.foldername(name))[1] = auth.uid()::text
        );
    $policy$;
  END IF;
END $$;

-- Policy 4: UPDATE — users can only update objects in their own folder.
-- (Required for Supabase Storage's multipart upload completion flow.)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname = 'documind_documents_update_own_folder'
  ) THEN
    EXECUTE $policy$
      CREATE POLICY documind_documents_update_own_folder
        ON storage.objects
        FOR UPDATE
        USING (
          bucket_id = 'documents'
          AND (storage.foldername(name))[1] = auth.uid()::text
        );
    $policy$;
  END IF;
END $$;
