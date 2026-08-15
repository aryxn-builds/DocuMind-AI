-- Migration: Add explicit INSERT RLS policy to public.processing_jobs
-- Ensures authenticated users can only insert jobs where user_id = auth.uid()

CREATE POLICY "Users can insert own processing_jobs"
ON public.processing_jobs
FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());
