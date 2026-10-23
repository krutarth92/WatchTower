import type {
	ActorRead,
	ActorResponse,
	AliasResponse,
	AssociationResponse,
	ReferenceResponse,
	TimelinePageResponse
} from '#lib/api/contracts.ts';
import {
	actorTimelineQuery,
	parseActorWorkspaceState,
	validActorId,
	type ParsedActorWorkspaceState
} from '#lib/actors/state.ts';
import { PublicApiError, publicApi, type PublicQuery } from '#lib/server/api/client.ts';

export interface ActorPanelError {
	status: number;
	message: string;
	requestId: string | null;
}

export type ActorPanel<T> =
	| { state: 'success'; data: T }
	| { state: 'error'; error: ActorPanelError };

export interface ActorPageData {
	view: 'success' | 'invalid' | 'unavailable';
	workspace: ParsedActorWorkspaceState;
	actor: ActorRead | null;
	actorError: ActorPanelError | null;
	panels: {
		aliases: ActorPanel<AliasResponse['data']> | null;
		associations: ActorPanel<AssociationResponse['data']> | null;
		timeline: ActorPanel<TimelinePageResponse> | null;
		references: ActorPanel<ReferenceResponse['data']> | null;
	};
}

export interface ActorClient {
	get<T>(path: string, query?: PublicQuery): Promise<T>;
}

const defaultClient: ActorClient = {
	get: (path, query = {}) => publicApi.get(path, query)
};

export function actorPanelError(caught: unknown, subject: string): ActorPanelError {
	const detail = caught instanceof PublicApiError ? caught.detail : null;
	return {
		status: detail?.status ?? 0,
		message:
			detail?.status === 429
				? `${subject} is temporarily rate limited. Wait a moment and retry.`
				: `${subject} is unavailable. Retry this section.`,
		requestId: detail?.requestId ?? null
	};
}

async function panel<T>(work: Promise<T>, subject: string): Promise<ActorPanel<T>> {
	try {
		return { state: 'success', data: await work };
	} catch (caught) {
		return { state: 'error', error: actorPanelError(caught, subject) };
	}
}

export async function loadActorPage(
	actorId: string,
	params: URLSearchParams,
	client: ActorClient = defaultClient
): Promise<ActorPageData> {
	const workspace = parseActorWorkspaceState(params);
	const emptyPanels = { aliases: null, associations: null, timeline: null, references: null };
	if (!validActorId(actorId) || workspace.errors.length) {
		return {
			view: 'invalid',
			workspace: !validActorId(actorId)
				? { ...workspace, errors: ['The actor identifier is invalid.', ...workspace.errors] }
				: workspace,
			actor: null,
			actorError: null,
			panels: emptyPanels
		};
	}

	let actor: ActorRead;
	try {
		actor = (await client.get<ActorResponse>(`/api/v1/actors/${actorId}`)).data;
	} catch (caught) {
		const detail = caught instanceof PublicApiError ? caught.detail : null;
		return {
			view: 'unavailable',
			workspace,
			actor: null,
			actorError: {
				status: detail?.status ?? 0,
				message:
					detail?.status === 404
						? 'This published record is unavailable.'
						: 'The actor workspace is unavailable. Check the local backend and try again.',
				requestId: detail?.requestId ?? null
			},
			panels: emptyPanels
		};
	}

	const base = `/api/v1/actors/${actorId}`;
	const [aliases, associations, timeline, references] = await Promise.all([
		panel(
			client.get<AliasResponse>(`${base}/aliases`).then((response) => response.data),
			'Aliases'
		),
		panel(
			client.get<AssociationResponse>(`${base}/associations`).then((response) => response.data),
			'Associations'
		),
		panel(
			client.get<TimelinePageResponse>(`${base}/timeline`, actorTimelineQuery(workspace.state)),
			'Timeline'
		),
		panel(
			client.get<ReferenceResponse>(`${base}/references`).then((response) => response.data),
			'References'
		)
	]);

	return {
		view: 'success',
		workspace,
		actor,
		actorError: null,
		panels: { aliases, associations, timeline, references }
	};
}
