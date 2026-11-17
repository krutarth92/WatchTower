import type { IsoDateTime, Uuid } from '#lib/api/contracts.ts';

export type IntegrationWave = 'implemented' | 'first_wave' | 'second_wave' | 'candidate';
export type EnrichmentWave = 'implemented' | 'first_wave' | 'later';
export type IngestionJobState = 'queued' | 'processing' | 'succeeded' | 'failed';

export interface IngestionJobRead {
	id: Uuid;
	job_kind: 'mitre_attack_refresh';
	source_id: Uuid;
	raw_evidence_id: Uuid | null;
	state: IngestionJobState;
	correlation_id: string;
	idempotency_key: string;
	attempts: number;
	max_attempts: number;
	failure_reason: string | null;
	next_attempt_at: IsoDateTime | null;
	started_at: IsoDateTime | null;
	finished_at: IsoDateTime | null;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface IntegrationRead {
	key: string;
	name: string;
	wave: IntegrationWave;
	description: string;
	status: 'available' | 'planned' | 'candidate';
	implemented: boolean;
	configured: boolean;
	can_sync: boolean;
	required_settings: string[];
	enrichments: string[];
	latest_job: IngestionJobRead | null;
}

export interface EnrichmentRead {
	key: string;
	name: string;
	wave: EnrichmentWave;
	description: string;
	implemented: boolean;
}

export interface IntegrationCatalogResponse {
	data: IntegrationRead[];
	enrichment_roadmap: EnrichmentRead[];
}

export interface IntegrationSyncResponse {
	data: {
		job: IngestionJobRead;
		duplicate: boolean;
	};
}
