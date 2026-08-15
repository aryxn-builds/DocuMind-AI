-- ==========================================================================================
-- DocuMind AI — Security Fixes (Phase 6 Audit)
-- ==========================================================================================

-- 1. Fix collection_documents RLS (INSERT)
-- Prevents User A from inserting User B's document into User A's collection.

DROP POLICY IF EXISTS "Users can create own collection_documents" ON public.collection_documents;

CREATE POLICY "Users can create own collection_documents" ON public.collection_documents FOR INSERT 
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.collections c WHERE c.id = collection_documents.collection_id AND c.user_id = auth.uid()
  )
  AND
  EXISTS (
    SELECT 1 FROM public.documents d WHERE d.id = collection_documents.document_id AND d.user_id = auth.uid()
  )
);


-- 2. Fix Profile Trigger Search Path
-- Hardens the SECURITY DEFINER function against search path injection attacks.

CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, avatar_url)
  VALUES (
    new.id, 
    new.email, 
    new.raw_user_meta_data->>'full_name', 
    new.raw_user_meta_data->>'avatar_url'
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
