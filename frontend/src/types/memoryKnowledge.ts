export interface MemoryEvidence {
  source_id: string
  role: 'user' | 'assistant'
  quote: string
  occurred_at: string
}

export interface MemoryKnowledge {
  kind?: 'entity' | 'fact'
  entity_type?: string
  aliases?: string[]
  subject_id?: string
  predicate?: string
  object_id?: string
  evidence?: MemoryEvidence[]
  status?: string
}

export interface KnowledgeStats {
  entities: number
  facts: number
  pending_sources: number
  available?: boolean
  sources_processed?: number
  entities_created?: number
  facts_created?: number
}
