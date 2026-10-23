export type IntelligenceType = 'observed' | 'assessed';
export type Origin = 'imported' | 'watchtower';
export type IsoDateTime = string;
export type Uuid = string;

export interface ApiErrorDetail {
	location: string;
	message: string;
	type: string;
}

export interface ApiErrorBody {
	code: string;
	message: string;
	request_id: string;
	details: ApiErrorDetail[];
}

export interface ApiErrorResponse {
	error: ApiErrorBody;
}

export interface SourceRead {
	id: Uuid;
	name: string;
	kind: string;
	base_url: string | null;
}

export interface ActorRead {
	id: Uuid;
	canonical_name: string;
	description: string | null;
}

export interface ActorResponse {
	data: ActorRead;
}

export interface ActorSearchRead extends ActorRead {
	matched_names: string[];
}

export interface ActorSearchResponse {
	data: ActorSearchRead[];
	limit: number;
}

export interface AliasRead {
	id: Uuid;
	name: string;
	source_native_id: string | null;
	confidence: number | null;
	source: SourceRead;
}

export interface AliasResponse {
	data: { items: AliasRead[]; truncated: boolean };
}

export interface BehaviorRead {
	id: Uuid;
	name: string;
	description: string | null;
}

export interface TechniqueRead {
	id: Uuid;
	external_id: string;
	name: string;
	description: string | null;
	source: SourceRead;
}

export interface EvidenceRead {
	id: Uuid;
	citation: string;
	excerpt: string | null;
	locator: string | null;
	captured_at: IsoDateTime | null;
	confidence: number | null;
	origin: Origin;
	raw_evidence_id: Uuid | null;
	source: SourceRead;
}

export interface ObservationRead {
	id: Uuid;
	source_native_id: string | null;
	title: string;
	summary: string;
	observed_at: IsoDateTime;
	first_seen: IsoDateTime | null;
	last_seen: IsoDateTime | null;
	confidence: number | null;
	intelligence_type: IntelligenceType;
	origin: Origin;
	raw_evidence_id: Uuid | null;
	source: SourceRead;
	evidence: EvidenceRead[];
	behaviors: BehaviorRead[];
	techniques: TechniqueRead[];
	evidence_truncated: boolean;
	behaviors_truncated: boolean;
	techniques_truncated: boolean;
}

export interface CursorPage {
	limit: number;
	next_cursor: string | null;
}

export interface ObservationPageResponse {
	data: ObservationRead[];
	page: CursorPage;
}

export interface TimelineEvent extends ObservationRead {
	event_type: 'observation';
}

export interface TimelinePageResponse {
	data: TimelineEvent[];
	page: CursorPage;
}

export interface AssociationResponse {
	data: {
		behaviors: BehaviorRead[];
		techniques: TechniqueRead[];
		behaviors_truncated: boolean;
		techniques_truncated: boolean;
	};
}

export interface ReferenceResponse {
	data: {
		sources: SourceRead[];
		evidence: EvidenceRead[];
		sources_truncated: boolean;
		evidence_truncated: boolean;
	};
}

export type SearchEntityType =
	| 'actor'
	| 'alias'
	| 'campaign'
	| 'behavior'
	| 'technique'
	| 'observation'
	| 'source'
	| 'indicator'
	| 'vulnerability';

export interface RelatedActorRead {
	id: Uuid;
	canonical_name: string;
	description: string | null;
	latest_observed_at: IsoDateTime | null;
}

export interface SearchResultRead {
	entity_type: SearchEntityType;
	id: Uuid;
	title: string;
	summary: string | null;
	source_id: Uuid | null;
	actor_id: Uuid | null;
	external_id: string | null;
	observed_at: IsoDateTime | null;
	intelligence_type: IntelligenceType | null;
	origin: Origin | null;
	indicator_type: string | null;
	indicator_value: string | null;
	severity: string | null;
	cvss_score: number | null;
	related_actors: RelatedActorRead[];
	related_actors_truncated: boolean;
	match_kind: 'exact' | 'full_text';
	score: number;
}

export interface SearchResponse {
	query: string;
	data: SearchResultRead[];
	limit: number;
	next_cursor: string | null;
}

export interface ActorDiscoveryRead {
	id: Uuid;
	canonical_name: string;
	description: string | null;
	latest_observed_at: IsoDateTime | null;
	published_observation_count: number;
	published_alias_count: number;
	popularity_score: number;
}

export interface ActorDiscoveryResponse {
	recent: ActorDiscoveryRead[];
	popular: ActorDiscoveryRead[];
	limit: number;
}

export type AdvisorySectionType =
	| 'what_happened'
	| 'actor_context'
	| 'technical_analysis'
	| 'detection'
	| 'response'
	| 'mitigation'
	| 'watchtower_assessment';

export interface EvidenceLinkRead {
	id: Uuid;
	citation: string;
	excerpt: string | null;
	source_id: Uuid;
}

export interface NamedLinkRead {
	id: Uuid;
	name: string;
}

export interface ActorLinkRead {
	id: Uuid;
	canonical_name: string;
}

export interface TechniqueLinkRead extends NamedLinkRead {
	external_id: string;
}

export interface SectionRead {
	section_type: AdvisorySectionType;
	position: number;
	intelligence_type: IntelligenceType;
	content: string;
}

export interface RevisionRead {
	id: Uuid;
	version: number;
	title: string;
	summary: string;
	created_by: string;
	created_at: IsoDateTime;
	published_at: IsoDateTime | null;
	published_by: string | null;
	sections: SectionRead[];
	evidence: EvidenceLinkRead[];
	actors: ActorLinkRead[];
	campaigns: NamedLinkRead[];
	techniques: TechniqueLinkRead[];
}

export interface UpdateRead {
	id: Uuid;
	sequence: number;
	revision_version: number;
	occurred_at: IsoDateTime;
	title: string;
	summary: string;
	intelligence_type: IntelligenceType;
	created_by: string;
	created_at: IsoDateTime;
	evidence: EvidenceLinkRead[];
}

export interface AdvisoryRead {
	id: Uuid;
	slug: string;
	status: 'draft' | 'published';
	published_revision: number | null;
	published_at: IsoDateTime | null;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
	revision: RevisionRead;
	updates: UpdateRead[];
}

export interface AdvisorySummaryRead {
	id: Uuid;
	slug: string;
	title: string;
	summary: string;
	published_revision: number;
	published_at: IsoDateTime;
	latest_update_at: IsoDateTime | null;
}

export interface AdvisoryResponse {
	data: AdvisoryRead;
}

export interface AdvisoryCollectionResponse {
	data: AdvisorySummaryRead[];
	limit: number;
}

export interface UpdateCollectionResponse {
	data: UpdateRead[];
	after_sequence: number;
	limit: number;
}
