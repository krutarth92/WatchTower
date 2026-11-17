import { json } from '@sveltejs/kit';
import type { UpdateCollectionResponse } from '#lib/api/contracts.ts';
import { PublicApiError, publicApi } from '#lib/server/api/client.ts';
import { validAdvisorySlug } from '#lib/server/advisories/page.ts';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ params, request }) => {
	if (!validAdvisorySlug(params.slug)) {
		return json({ error: { message: 'This published record is unavailable.' } }, { status: 404 });
	}

	let afterSequence: unknown;
	try {
		({ afterSequence } = (await request.json()) as { afterSequence?: unknown });
	} catch {
		return json({ error: { message: 'The update cursor is invalid.' } }, { status: 400 });
	}
	if (!Number.isSafeInteger(afterSequence) || Number(afterSequence) < 1) {
		return json({ error: { message: 'The update cursor is invalid.' } }, { status: 400 });
	}

	try {
		const response = await publicApi.get<UpdateCollectionResponse>(
			`/api/v1/advisories/${params.slug}/updates`,
			{ after_sequence: Number(afterSequence), limit: 25 }
		);
		return json({ data: response.data });
	} catch (caught) {
		const detail = caught instanceof PublicApiError ? caught.detail : null;
		return json(
			{
				error: {
					message: 'More advisory updates could not be loaded.',
					requestId: detail?.requestId ?? null
				}
			},
			{ status: detail?.status && detail.status >= 400 ? detail.status : 502 }
		);
	}
};
