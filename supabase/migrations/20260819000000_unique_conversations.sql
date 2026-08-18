-- Migration to enforce one active conversation per (user_id, document_id)

-- 1. Deduplicate existing conversations
-- Keep the conversation with the most messages (or most recent) for each document
WITH ranked_conversations AS (
    SELECT 
        c.id,
        c.user_id,
        c.document_id,
        COUNT(m.id) as message_count,
        ROW_NUMBER() OVER (
            PARTITION BY c.user_id, c.document_id 
            ORDER BY COUNT(m.id) DESC, c.updated_at DESC, c.created_at DESC
        ) as rn
    FROM conversations c
    LEFT JOIN messages m ON c.id = m.conversation_id
    WHERE c.document_id IS NOT NULL
    GROUP BY c.id, c.user_id, c.document_id, c.updated_at, c.created_at
)
DELETE FROM conversations
WHERE id IN (
    SELECT id FROM ranked_conversations WHERE rn > 1
);

-- 2. Add a UNIQUE constraint
-- In PostgreSQL, a UNIQUE constraint on (user_id, document_id) allows multiple
-- rows where document_id IS NULL (because NULL != NULL). Thus, multi-document
-- conversations are unaffected, but single-document conversations are restricted to 1.
CREATE UNIQUE INDEX idx_conversations_unique_user_doc 
ON conversations (user_id, document_id) 
WHERE document_id IS NOT NULL;
