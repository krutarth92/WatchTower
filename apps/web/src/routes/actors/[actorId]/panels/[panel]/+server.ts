import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import type {
	AliasResponse,
	AssociationResponse,
	ReferenceResponse,
	TimelinePageResponse
} from '#lib/api/contracts.ts';
import { actorTimelineQuery, parseActorWorkspaceState, validActorId } from '#lib/actors/state.ts';
import { publicApi } from '#lib/server/api/client.ts';
import { actorPanelError } from '#lib/server/actors/page.ts';

const panels = ['aliases', 'associations', 'timeline', 'references'] as const;
type PanelName = (typeof panels)[number];

function panelName(value: string): value is PanelName {
	return panels.includes(value as PanelName);
}

export const POST: RequestHandler = async ({ params, request, url }) => {
	if (!validActorId(params.actorId) || !panelName(params.panel)) {
		return json(
			{ error: { message: 'The actor panel request is invalid.', requestId: null } },
			{ status: 422, headers: { 'Cache-Control': 'no-store' } }
		);
	}

	const workspace = parseActorWorkspaceState(url.searchParams);
	if (workspace.errors.length) {
		return json(
			{ error: { message: 'The actor workspace filters are invalid.', requestId: null } },
			{ status: 422, headers: { 'Cache-Control': 'no-store' } }
		);
	}

	let cursor: string | undefined;
	if (params.panel === 'timeline') {
		try {
			const value = ((await request.json()) as { cursor?: unknown }).cursor;
			if (value !== undefined && value !== null) {
				if (typeof value !== 'string' || !value || value.length > 1024) throw new Error();
				cursor = value;
			}
		} catch {
			return json(
				{ error: { message: 'The timeline cursor is invalid.', requestId: null } },
				{ status: 422, headers: { 'Cache-Control': 'no-store' } }
			);
		}
	}

	const base = `/api/v1/actors/${params.actorId}`;
	try {
		let data: unknown;
		if (params.panel === 'aliases') {
			data = (await publicApi.get<AliasResponse>(`${base}/aliases`)).data;
		} else if (params.panel === 'associations') {
			data = (await publicApi.get<AssociationResponse>(`${base}/associations`)).data;
		} else if (params.panel === 'references') {
			data = (await publicApi.get<ReferenceResponse>(`${base}/references`)).data;
		} else {
			data = await publicApi.get<TimelinePageResponse>(
				`${base}/timeline`,
				actorTimelineQuery(workspace.state, cursor)
			);
		}
		return json({ data }, { headers: { 'Cache-Control': 'no-store' } });
	} catch (caught) {
		const error = actorPanelError(
			caught,
			params.panel === 'timeline'
				? 'Timeline'
				: params.panel.charAt(0).toUpperCase() + params.panel.slice(1)
		);
		return json(
			{ error },
			{ status: error.status === 429 ? 429 : 503, headers: { 'Cache-Control': 'no-store' } }
		);
	}
};
