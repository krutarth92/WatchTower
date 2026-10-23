import type { IntelligenceType, SearchEntityType } from '#lib/api/contracts.ts';

export const searchEntityTypes = [
	'actor',
	'alias',
	'campaign',
	'behavior',
	'technique',
	'observation',
	'source'
] as const satisfies readonly SearchEntityType[];

export const searchIntelligenceTypes = [
	'observed',
	'assessed'
] as const satisfies readonly IntelligenceType[];

const supportedKeys = new Set([
	'q',
	'entity_type',
	'intelligence_type',
	'source_id',
	'date_from',
	'date_to'
]);
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const datePattern = /^\d{4}-\d{2}-\d{2}$/;

export interface SearchState {
	query: string;
	entityTypes: SearchEntityType[];
	intelligenceType: IntelligenceType | '';
	sourceId: string;
	dateFrom: string;
	dateTo: string;
}

export interface SearchStateResult {
	state: SearchState;
	errors: string[];
	submitted: boolean;
}

function scalar(params: URLSearchParams, key: string, errors: string[]): string {
	const values = params.getAll(key);
	if (values.length > 1) errors.push(`${key} must be supplied once.`);
	return values[0]?.trim() ?? '';
}

function validDate(value: string): boolean {
	if (!datePattern.test(value)) return false;
	const parsed = new Date(`${value}T00:00:00.000Z`);
	return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().startsWith(value);
}

export function parseSearchState(params: URLSearchParams): SearchStateResult {
	const errors: string[] = [];
	for (const key of new Set(params.keys())) {
		if (!supportedKeys.has(key)) errors.push(`Unsupported search parameter: ${key}.`);
	}

	const query = scalar(params, 'q', errors).replace(/\s+/g, ' ');
	const rawEntityTypes = params.getAll('entity_type');
	const selected = new Set<SearchEntityType>();
	for (const value of rawEntityTypes) {
		if (!searchEntityTypes.includes(value as SearchEntityType)) {
			errors.push(`Unsupported entity type: ${value || '(empty)'}.`);
		} else {
			selected.add(value as SearchEntityType);
		}
	}
	const entityTypes = searchEntityTypes.filter((value) => selected.has(value));

	const rawIntelligenceType = scalar(params, 'intelligence_type', errors);
	const intelligenceType = searchIntelligenceTypes.includes(rawIntelligenceType as IntelligenceType)
		? (rawIntelligenceType as IntelligenceType)
		: '';
	if (rawIntelligenceType && !intelligenceType) {
		errors.push(`Unsupported intelligence type: ${rawIntelligenceType}.`);
	}

	const sourceId = scalar(params, 'source_id', errors);
	const dateFrom = scalar(params, 'date_from', errors);
	const dateTo = scalar(params, 'date_to', errors);
	const submitted = params.size > 0;

	if (submitted) {
		if (query.length < 2) errors.push('Enter at least two non-whitespace characters.');
		if (query.length > 200) errors.push('Search queries cannot exceed 200 characters.');
		if (/\p{Cc}/u.test(query)) errors.push('Search queries cannot contain control characters.');
	}
	if (sourceId && !uuidPattern.test(sourceId)) errors.push('Source ID must be a valid UUID.');
	if (dateFrom && !validDate(dateFrom)) errors.push('Start date must be a valid UTC date.');
	if (dateTo && !validDate(dateTo)) errors.push('End date must be a valid UTC date.');
	if (dateFrom && dateTo && validDate(dateFrom) && validDate(dateTo) && dateFrom > dateTo) {
		errors.push('Start date must be earlier than or equal to end date.');
	}

	return {
		state: { query, entityTypes, intelligenceType, sourceId, dateFrom, dateTo },
		errors: [...new Set(errors)],
		submitted
	};
}

export function serializeSearchState(state: SearchState): URLSearchParams {
	const params = new URLSearchParams();
	if (state.query) params.set('q', state.query);
	for (const entityType of searchEntityTypes) {
		if (state.entityTypes.includes(entityType)) params.append('entity_type', entityType);
	}
	if (state.intelligenceType) params.set('intelligence_type', state.intelligenceType);
	if (state.sourceId) params.set('source_id', state.sourceId.toLowerCase());
	if (state.dateFrom) params.set('date_from', state.dateFrom);
	if (state.dateTo) params.set('date_to', state.dateTo);
	return params;
}

export function backendSearchQuery(
	state: SearchState,
	cursor?: string
): Readonly<Record<string, string | number | readonly string[] | undefined>> {
	return {
		q: state.query,
		entity_type: state.entityTypes.length ? state.entityTypes : undefined,
		intelligence_type: state.intelligenceType || undefined,
		source_id: state.sourceId ? state.sourceId.toLowerCase() : undefined,
		date_from: state.dateFrom ? `${state.dateFrom}T00:00:00.000Z` : undefined,
		date_to: state.dateTo ? `${state.dateTo}T23:59:59.999Z` : undefined,
		limit: 25,
		cursor
	};
}
