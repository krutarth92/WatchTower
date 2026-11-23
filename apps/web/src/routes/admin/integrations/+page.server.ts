import { error, fail } from '@sveltejs/kit';
import {
	operatorApi,
	OperatorApiError,
	type SyncIntegrationKey
} from '#lib/server/api/operator-client.ts';
import { runtimeConfig } from '#lib/server/config/runtime.ts';
import type { Actions, PageServerLoad } from './$types';

function requireAdmin() {
	if (!runtimeConfig.adminEnabled) error(404, 'Not found');
}

export const load: PageServerLoad = async () => {
	requireAdmin();
	try {
		return {
			catalog: await operatorApi.catalog(),
			idempotencyKey: `watchtower-ui-${crypto.randomUUID()}`,
			loadError: null
		};
	} catch (caught) {
		const detail =
			caught instanceof OperatorApiError
				? caught.detail
				: {
						message: 'Integration management is temporarily unavailable.',
						requestId: null
					};
		return {
			catalog: null,
			idempotencyKey: `watchtower-ui-${crypto.randomUUID()}`,
			loadError: { message: detail.message, requestId: detail.requestId }
		};
	}
};

export const actions: Actions = {
	sync: async ({ request }) => {
		requireAdmin();
		const form = await request.formData();
		const integrationKey = form.get('integration_key');
		const idempotencyKey = form.get('idempotency_key');
		const syncable = {
			'mitre-attack': 'MITRE ATT&CK',
			'misp-galaxy': 'MISP Galaxy',
			cisa: 'CISA KEV',
			'microsoft-threat-intelligence': 'Microsoft Threat Intelligence',
			'unit-42': 'Unit 42',
			'the-hacker-news': 'The Hacker News'
		} as const satisfies Record<SyncIntegrationKey, string>;
		if (
			typeof integrationKey !== 'string' ||
			!(integrationKey in syncable) ||
			typeof idempotencyKey !== 'string' ||
			!/^watchtower-ui-[0-9a-f-]{36}$/.test(idempotencyKey)
		) {
			return fail(400, {
				ok: false,
				message: 'The integration request was invalid.',
				requestId: null
			});
		}

		try {
			const response = await operatorApi.sync(integrationKey as SyncIntegrationKey, idempotencyKey);
			const sourceName = syncable[integrationKey as SyncIntegrationKey];
			return {
				ok: true,
				duplicate: response.data.duplicate,
				state: response.data.job.state,
				requestId: null,
				message: response.data.duplicate
					? `The existing ${sourceName} refresh is already queued.`
					: `${sourceName} refresh queued.`
			};
		} catch (caught) {
			const detail =
				caught instanceof OperatorApiError
					? caught.detail
					: {
							status: 502,
							message: 'The integration request could not be completed.',
							requestId: null
						};
			return fail(detail.status >= 400 && detail.status < 600 ? detail.status : 502, {
				ok: false,
				message: detail.message,
				requestId: detail.requestId
			});
		}
	}
};
