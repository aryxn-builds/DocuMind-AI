-- ==========================================================================================
-- DocuMind AI — Initial Database Schema & RLS
-- Source: DATABASE_SCHEMA.md and SECURITY.md
-- ==========================================================================================

-- 1. Create Tables
-- ------------------------------------------------------------------------------------------

CREATE TABLE public.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email text NOT NULL UNIQUE,
    full_name text,
    avatar_url text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title text NOT NULL,
    original_filename text NOT NULL,
    file_path text NOT NULL,
    file_type text NOT NULL,
    file_size_bytes bigint NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    page_count int,
    processing_metadata jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.document_chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    chunk_index int NOT NULL,
    content_preview text,
    chunk_type text NOT NULL DEFAULT 'text',
    page_number int,
    position_metadata jsonb,
    qdrant_point_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    document_id uuid REFERENCES public.documents(id) ON DELETE SET NULL,
    title text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role text NOT NULL,
    content text NOT NULL,
    metadata jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.citations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id uuid NOT NULL REFERENCES public.messages(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    document_chunk_id uuid NOT NULL REFERENCES public.document_chunks(id) ON DELETE CASCADE,
    document_id uuid NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    page_number int,
    excerpt text,
    relevance_score float,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.collections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name text NOT NULL,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.collection_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id uuid NOT NULL REFERENCES public.collections(id) ON DELETE CASCADE,
    document_id uuid NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    added_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(collection_id, document_id)
);

CREATE TABLE public.processing_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    job_type text NOT NULL DEFAULT 'ingestion',
    status text NOT NULL DEFAULT 'queued',
    progress float,
    error_details jsonb,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Create Indexes
-- ------------------------------------------------------------------------------------------

CREATE INDEX idx_documents_user_id ON public.documents(user_id);
CREATE INDEX idx_documents_status ON public.documents(status);
CREATE INDEX idx_documents_user_id_created_at ON public.documents(user_id, created_at DESC);

CREATE INDEX idx_chunks_document_id ON public.document_chunks(document_id);
CREATE INDEX idx_chunks_user_id ON public.document_chunks(user_id);
CREATE UNIQUE INDEX idx_chunks_qdrant_point_id ON public.document_chunks(qdrant_point_id);

CREATE INDEX idx_conversations_user_id ON public.conversations(user_id);
CREATE INDEX idx_conversations_user_id_updated_at ON public.conversations(user_id, updated_at DESC);

CREATE INDEX idx_messages_conversation_id ON public.messages(conversation_id);
CREATE INDEX idx_messages_conversation_id_created_at ON public.messages(conversation_id, created_at ASC);

CREATE INDEX idx_citations_message_id ON public.citations(message_id);
CREATE INDEX idx_citations_user_id ON public.citations(user_id);
CREATE INDEX idx_citations_document_id ON public.citations(document_id);

CREATE INDEX idx_collections_user_id ON public.collections(user_id);
CREATE INDEX idx_collection_documents_collection_id ON public.collection_documents(collection_id);

CREATE INDEX idx_jobs_document_id ON public.processing_jobs(document_id);
CREATE INDEX idx_jobs_user_id_status ON public.processing_jobs(user_id, status);

-- 3. Trigger for new user creation
-- ------------------------------------------------------------------------------------------

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
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 4. Enable Row Level Security
-- ------------------------------------------------------------------------------------------

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collection_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processing_jobs ENABLE ROW LEVEL SECURITY;

-- 5. Create RLS Policies
-- ------------------------------------------------------------------------------------------

-- profiles
CREATE POLICY "Users can view own profiles" ON public.profiles FOR SELECT USING (id = auth.uid());
CREATE POLICY "Users can update own profiles" ON public.profiles FOR UPDATE USING (id = auth.uid());

-- documents
CREATE POLICY "Users can view own documents" ON public.documents FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can create own documents" ON public.documents FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Users can update own documents" ON public.documents FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Users can delete own documents" ON public.documents FOR DELETE USING (user_id = auth.uid());

-- document_chunks
CREATE POLICY "Users can view own document_chunks" ON public.document_chunks FOR SELECT USING (user_id = auth.uid());
-- Insert/Update/Delete handled by service role

-- conversations
CREATE POLICY "Users can view own conversations" ON public.conversations FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can create own conversations" ON public.conversations FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Users can update own conversations" ON public.conversations FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Users can delete own conversations" ON public.conversations FOR DELETE USING (user_id = auth.uid());

-- messages
CREATE POLICY "Users can view own messages" ON public.messages FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can create own messages" ON public.messages FOR INSERT WITH CHECK (user_id = auth.uid());
-- Updates/Deletes typically handled by service role or not allowed

-- citations
CREATE POLICY "Users can view own citations" ON public.citations FOR SELECT USING (user_id = auth.uid());
-- Insert handled by service role (or user if streaming directly, but typically service role during generation)
CREATE POLICY "Users can create own citations" ON public.citations FOR INSERT WITH CHECK (user_id = auth.uid());

-- collections
CREATE POLICY "Users can view own collections" ON public.collections FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can create own collections" ON public.collections FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Users can update own collections" ON public.collections FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Users can delete own collections" ON public.collections FOR DELETE USING (user_id = auth.uid());

-- collection_documents (scoped via collection ownership)
-- user_id doesn't exist directly on collection_documents, so we join with collections table
CREATE POLICY "Users can view own collection_documents" ON public.collection_documents FOR SELECT 
USING (EXISTS (
  SELECT 1 FROM public.collections c WHERE c.id = collection_documents.collection_id AND c.user_id = auth.uid()
));
CREATE POLICY "Users can create own collection_documents" ON public.collection_documents FOR INSERT 
WITH CHECK (EXISTS (
  SELECT 1 FROM public.collections c WHERE c.id = collection_documents.collection_id AND c.user_id = auth.uid()
));
CREATE POLICY "Users can delete own collection_documents" ON public.collection_documents FOR DELETE 
USING (EXISTS (
  SELECT 1 FROM public.collections c WHERE c.id = collection_documents.collection_id AND c.user_id = auth.uid()
));

-- processing_jobs
CREATE POLICY "Users can view own processing_jobs" ON public.processing_jobs FOR SELECT USING (user_id = auth.uid());
-- Insert/Update/Delete handled by service role
