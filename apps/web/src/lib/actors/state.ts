import type { IntelligenceType } from '#lib/api/contracts.ts';
import { parseSearchState, serializeSearchState } from '#lib/search/state.ts';

export interface ActorWorkspaceState {
	dateFrom: string;
	dateTo: string;
	intelligenceType: '' | IntelligenceType;
	fromSearch: string;
}

export interface ParsedActorWorkspaceState {
	state: ActorWorkspaceState;
	errors: string[];
}

const allowedKeys = new Set(['date_from', 'date_to', 'intelligence_type', 'fromSearch']);
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function strictDate(value: string): boolean {
	if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
	const [year, month, day] = value.split('-').map(Number);
	const date = new Date(Date.UTC(year, month - 1, day));
	return (
		date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
	);
}

function normalizeSearchReturn(value: string): string | null {
	if (!value) return '/search';
	if (!value.startsWith('/search') || value.startsWith('//')) return null;
	try {
		const url = new URL(value, 'http://watchtower.local');
		if (url.origin !== 'http://watchtower.local' || url.pathname !== '/search' || url.hash) {
			return null;
		}
		const parsed = parseSearchState(url.searchParams);
		if (parsed.errors.length) return null;
		const query = serializeSearchState(parsed.state).toString();
		return `/search${query ? `?${query}` : ''}`;
	} catch {
		return null;
	}
}

export function validActorId(value: string): boolean {
	return uuidPattern.test(value);
}

export function parseActorWorkspaceState(params: URLSearchParams): ParsedActorWorkspaceState {
	const errors: string[] = [];
	for (const key of params.keys()) {
		if (!allowedKeys.has(key)) errors.push(`Unsupported actor workspace parameter: ${key}.`);
		if (params.getAll(key).length > 1) errors.push(`Parameter ${key} must appear only once.`);
	}

	const dateFrom = params.get('date_from')?.trim() ?? '';
	const dateTo = params.get('date_to')?.trim() ?? '';
	const intelligence = params.get('intelligence_type')?.trim() ?? '';
	const searchReturn = normalizeSearchReturn(params.get('fromSearch')?.trim() ?? '');

	if (dateFrom && !strictDate(dateFrom)) errors.push('From date must be a valid YYYY-MM-DD date.');
	if (dateTo && !strictDate(dateTo)) errors.push('To date must be a valid YYYY-MM-DD date.');
	if (dateFrom && dateTo && dateFrom > dateTo) {
		errors.push('From date must be earlier than or equal to the to date.');
	}
	if (intelligence && intelligence !== 'observed' && intelligence !== 'assessed') {
		errors.push('Intelligence type must be observed or assessed.');
	}
	if (searchReturn === null)
		errors.push('Search return path must be a valid WATCHTOWER search URL.');

	return {
		state: {
			dateFrom,
			dateTo,
			intelligenceType:
				intelligence === 'observed' || intelligence === 'assessed' ? intelligence : '',
			fromSearch: searchReturn ?? '/search'
		},
		errors: [...new Set(errors)]
	};
}

export function serializeActorWorkspaceState(state: ActorWorkspaceState): URLSearchParams {
	const params = new URLSearchParams();
	if (state.dateFrom) params.set('date_from', state.dateFrom);
	if (state.dateTo) params.set('date_to', state.dateTo);
	if (state.intelligenceType) params.set('intelligence_type', state.intelligenceType);
	if (state.fromSearch !== '/search') params.set('fromSearch', state.fromSearch);
	return params;
}

export function actorTimelineQuery(
	state: ActorWorkspaceState,
	cursor?: string
): Readonly<Record<string, string | number | undefined>> {
	return {
		date_from: state.dateFrom ? `${state.dateFrom}T00:00:00.000Z` : undefined,
		date_to: state.dateTo ? `${state.dateTo}T23:59:59.999Z` : undefined,
		intelligence_type: state.intelligenceType || undefined,
		limit: 25,
		cursor
	};
}
