import type { IsoDateTime, Uuid } from '#lib/api/contracts.ts';

export type IntegrationWave = 'implemented' | 'first_wave' | 'second_wave' | 'candidate';
export type EnrichmentWave = 'implemented' | 'first_wave' | 'later';
export type IngestionJobState = 'queued' | 'processing' | 'succeeded' | 'failed';
export type IngestionJobKind =
	| 'mitre_attack_refresh'
	| 'misp_galaxy_refresh'
	| 'cisa_kev_refresh'
	| 'microsoft_threat_intelligence_refresh'
	| 'unit_42_refresh'
	| 'the_hacker_news_refresh';

export interface IngestionJobRead {
	id: Uuid;
	job_kind: IngestionJobKind;
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
	job_kind: IngestionJobKind | null;
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
