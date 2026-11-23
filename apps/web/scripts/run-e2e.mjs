import { spawn } from 'node:child_process';
import { createServer as createHttpServer } from 'node:http';
import { createServer as createNetServer } from 'node:net';

const host = '127.0.0.1';
const port = await new Promise((resolve, reject) => {
	const probe = createNetServer();
	probe.once('error', reject);
	probe.listen(0, host, () => {
		const address = probe.address();
		if (!address || typeof address === 'string') {
			probe.close();
			reject(new Error('Could not reserve a local port for the production server.'));
			return;
		}

		probe.close((error) => (error ? reject(error) : resolve(String(address.port))));
	});
});
const baseUrl = `http://${host}:${port}`;
const operatorToken = 'task-35-browser-operator-token-with-32-characters';

const actorId = '20000000-0000-4000-8000-000000000001';
const partialActorId = '20000000-0000-4000-8000-000000000099';
const advisoryId = '80000000-0000-4000-8000-000000000001';
const advisorySlug = 'credential-access-evolution';
const source = {
	id: '10000000-0000-4000-8000-000000000001',
	name: 'Northstar Research',
	kind: 'report',
	base_url: 'https://example.test/research'
};

const evidence = (overrides = {}) => ({
	id: '30000000-0000-4000-8000-000000000001',
	citation: 'Northstar incident report, section 4',
	excerpt: 'The operator used a signed script before establishing persistence.',
	locator: 'https://example.test/research/midnight-blizzard',
	captured_at: '2026-03-11T11:30:00Z',
	confidence: 88,
	origin: 'imported',
	raw_evidence_id: null,
	source,
	...overrides
});

const timelineRecord = (overrides = {}) => ({
	id: '40000000-0000-4000-8000-000000000001',
	event_type: 'observation',
	source_native_id: 'northstar-42',
	title: 'PowerShell execution observed',
	summary: 'A published observation connected command execution to the actor.',
	observed_at: '2026-03-11T10:00:00Z',
	first_seen: '2026-03-10T09:00:00Z',
	last_seen: null,
	confidence: 88,
	intelligence_type: 'observed',
	origin: 'imported',
	raw_evidence_id: null,
	source,
	evidence: [evidence()],
	behaviors: [
		{
			id: '50000000-0000-4000-8000-000000000001',
			name: 'Command execution',
			description: 'Executes commands through an interpreter.'
		}
	],
	techniques: [
		{
			id: '60000000-0000-4000-8000-000000000001',
			external_id: 'T1059.001',
			name: 'PowerShell',
			description: 'PowerShell command execution.',
			source
		}
	],
	evidence_truncated: false,
	behaviors_truncated: false,
	techniques_truncated: false,
	...overrides
});

const advisoryRevision = (version = 2) => ({
	id: `81000000-0000-4000-8000-00000000000${version}`,
	version,
	title: version === 1 ? 'Credential access activity' : 'Credential access activity evolves',
	summary:
		'Published analysis of actor behavior, affected techniques and evidence-backed change over time.',
	created_by: 'watchtower-analyst',
	created_at: '2026-10-21T09:00:00Z',
	published_at: version === 1 ? '2026-10-21T10:00:00Z' : '2026-10-22T10:00:00Z',
	published_by: 'watchtower-publisher',
	sections: [
		{
			section_type: 'what_happened',
			position: 0,
			intelligence_type: 'observed',
			content: 'Published telemetry connected the actor to a new credential access sequence.'
		},
		{
			section_type: 'watchtower_assessment',
			position: 1,
			intelligence_type: 'assessed',
			content:
				'WATCHTOWER assesses this as an evolution of the previously documented workflow.'
		}
	],
	evidence: [
		{
			id: '30000000-0000-4000-8000-000000000001',
			citation: 'Northstar incident report, section 4',
			excerpt: 'The operator changed its credential collection sequence.',
			source_id: source.id
		}
	],
	actors: [{ id: actorId, canonical_name: 'Midnight Blizzard' }],
	campaigns: [{ id: '82000000-0000-4000-8000-000000000001', name: 'Northstar' }],
	techniques: [
		{
			id: '60000000-0000-4000-8000-000000000001',
			name: 'PowerShell',
			external_id: 'T1059.001'
		}
	]
});

const advisoryUpdate = {
	id: '83000000-0000-4000-8000-000000000001',
	sequence: 1,
	revision_version: 2,
	occurred_at: '2026-10-23T12:00:00Z',
	title: 'Detection guidance updated',
	summary: 'A new observed detection pattern was linked.',
	intelligence_type: 'observed',
	created_by: 'watchtower-analyst',
	created_at: '2026-10-23T12:30:00Z',
	evidence: []
};

const advisoryResponse = (version = 2) => ({
	data: {
		id: advisoryId,
		slug: advisorySlug,
		status: 'published',
		published_revision: 2,
		published_at: '2026-10-22T10:00:00Z',
		created_at: '2026-10-21T09:00:00Z',
		updated_at: '2026-10-23T12:30:00Z',
		revision: advisoryRevision(version),
		updates: [advisoryUpdate]
	}
});

const searchRecord = (overrides) => ({
	entity_type: 'actor',
	id: '20000000-0000-4000-8000-000000000001',
	title: 'Midnight Blizzard',
	summary: 'Published actor intelligence from the deterministic test API.',
	source_id: '10000000-0000-4000-8000-000000000001',
	actor_id: actorId,
	external_id: null,
	observed_at: '2026-01-02T03:04:05Z',
	intelligence_type: 'observed',
	origin: 'imported',
	indicator_type: null,
	indicator_value: null,
	severity: null,
	cvss_score: null,
	related_actors: [],
	related_actors_truncated: false,
	match_kind: 'exact',
	score: 100.25,
	...overrides
});

const integrationJob = (idempotencyKey) => ({
	id: '90000000-0000-4000-8000-000000000001',
	job_kind: 'mitre_attack_refresh',
	source_id: source.id,
	raw_evidence_id: null,
	state: 'queued',
	correlation_id: 'task-35-e2e',
	idempotency_key: idempotencyKey,
	attempts: 0,
	max_attempts: 3,
	failure_reason: null,
	next_attempt_at: '2026-11-17T10:00:00Z',
	started_at: null,
	finished_at: null,
	created_at: '2026-11-17T10:00:00Z',
	updated_at: '2026-11-17T10:00:00Z'
});

let latestIntegrationJob = null;

const integrationCatalog = () => ({
	data: [
		{
			key: 'mitre-attack',
			name: 'MITRE ATT&CK Enterprise',
			wave: 'implemented',
			description: 'Versioned ATT&CK STIX data for actors, techniques and mappings.',
			status: 'available',
			implemented: true,
			configured: true,
			can_sync: true,
			job_kind: 'mitre_attack_refresh',
			required_settings: [],
			enrichments: ['ATT&CK mappings', 'alias resolution', 'historical correlation'],
			latest_job: latestIntegrationJob
		},
		...[
			['misp-galaxy', 'MISP Galaxy', 'implemented', 'misp_galaxy_refresh'],
			['cisa', 'CISA KEV', 'implemented', 'cisa_kev_refresh'],
			[
				'microsoft-threat-intelligence',
				'Microsoft Threat Intelligence',
				'implemented',
				'microsoft_threat_intelligence_refresh'
			],
			['unit-42', 'Unit 42', 'implemented', 'unit_42_refresh'],
			['the-hacker-news', 'The Hacker News', 'implemented', 'the_hacker_news_refresh']
		].map(([key, name, wave, jobKind]) => ({
			key,
			name,
			wave,
			description: `${name} is available through a bounded source connector.`,
			status: 'available',
			implemented: true,
			configured: true,
			can_sync: true,
			job_kind: jobKind,
			required_settings: [],
			enrichments: ['historical correlation'],
			latest_job: null
		})),
		...[
			['google-tag', 'Google Threat Analysis Group', 'first_wave', []],
			['malpedia', 'Malpedia', 'second_wave', ['WATCHTOWER_MALPEDIA_API_KEY']],
			['securelist', 'Securelist', 'second_wave', []],
			['eset-research', 'ESET Research', 'second_wave', []],
			['selected-news', 'Selected news sources', 'second_wave', []]
		].map(([key, name, wave, requiredSettings]) => ({
			key,
			name,
			wave,
			description: `${name} is approved for a later connector stage.`,
			status: 'planned',
			implemented: false,
			configured: false,
			can_sync: false,
			job_kind: null,
			required_settings: requiredSettings,
			enrichments: ['historical correlation'],
			latest_job: null
		}))
	],
	enrichment_roadmap: [
		{
			key: 'attack-mapping',
			name: 'ATT&CK mappings',
			wave: 'implemented',
			description: 'Connect source behaviors to versioned ATT&CK techniques.',
			implemented: true
		},
		{
			key: 'alias-resolution',
			name: 'Alias resolution',
			wave: 'implemented',
			description: 'Resolve source names to canonical actor identities with provenance.',
			implemented: true
		},
		{
			key: 'historical-correlation',
			name: 'Historical correlation',
			wave: 'implemented',
			description: 'Retain observations for comparison over time.',
			implemented: true
		},
		{
			key: 'geoip-asn',
			name: 'Basic GeoIP and ASN',
			wave: 'first_wave',
			description: 'Add network ownership and geography context with provenance.',
			implemented: false
		},
		{
			key: 'external-reputation',
			name: 'External reputation APIs',
			wave: 'later',
			description: 'Add when a defined use case justifies the dependency.',
			implemented: false
		}
	]
});

const mockApi = createHttpServer(async (request, response) => {
	const requestUrl = new URL(request.url ?? '/', 'http://mock-api');
	response.setHeader('content-type', 'application/json');
	const sendError = (status, code, requestId) => {
		response.statusCode = status;
		response.end(
			JSON.stringify({
				error: {
					code,
					message: 'Mock internal detail.',
					request_id: requestId,
					details: []
				}
			})
		);
	};

	if (requestUrl.pathname === '/api/v1/operations/integrations') {
		if (request.headers['x-watchtower-operator-token'] !== operatorToken) {
			sendError(401, 'operator_auth_failed', 'mock-operator-401');
			return;
		}
		response.end(JSON.stringify(integrationCatalog()));
		return;
	}

	if (requestUrl.pathname === '/api/v1/operations/integrations/mitre-attack/sync') {
		if (request.headers['x-watchtower-operator-token'] !== operatorToken) {
			sendError(401, 'operator_auth_failed', 'mock-operator-401');
			return;
		}
		const chunks = [];
		for await (const chunk of request) chunks.push(chunk);
		const body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
		const duplicate = latestIntegrationJob?.idempotency_key === body.idempotency_key;
		latestIntegrationJob = integrationJob(body.idempotency_key);
		response.statusCode = 202;
		response.end(JSON.stringify({ data: { job: latestIntegrationJob, duplicate } }));
		return;
	}

	if (requestUrl.pathname === '/api/v1/search/discovery') {
		const actor = {
			id: actorId,
			canonical_name: 'Midnight Blizzard',
			description: 'Published adversary identity with source-linked evolution.',
			latest_observed_at: '2026-03-11T10:00:00Z',
			published_observation_count: 4,
			published_alias_count: 2,
			popularity_score: 26
		};
		response.end(JSON.stringify({ recent: [actor], popular: [actor], limit: 12 }));
		return;
	}

	if (requestUrl.pathname === '/api/v1/advisories') {
		response.end(
			JSON.stringify({
				data: [
					{
						id: advisoryId,
						slug: advisorySlug,
						title: advisoryRevision().title,
						summary: advisoryRevision().summary,
						published_revision: 2,
						published_at: '2026-10-22T10:00:00Z',
						latest_update_at: advisoryUpdate.occurred_at
					}
				],
				limit: Number(requestUrl.searchParams.get('limit') ?? 25)
			})
		);
		return;
	}

	if (requestUrl.pathname === `/api/v1/advisories/${advisorySlug}`) {
		response.end(JSON.stringify(advisoryResponse()));
		return;
	}

	if (requestUrl.pathname === `/api/v1/advisories/${advisorySlug}/revisions/1`) {
		response.end(JSON.stringify(advisoryResponse(1)));
		return;
	}

	if (requestUrl.pathname === `/api/v1/advisories/${advisorySlug}/updates`) {
		const after = Number(requestUrl.searchParams.get('after_sequence') ?? 0);
		response.end(
			JSON.stringify({
				data: after < advisoryUpdate.sequence ? [advisoryUpdate] : [],
				after_sequence: after,
				limit: Number(requestUrl.searchParams.get('limit') ?? 25)
			})
		);
		return;
	}

	if (requestUrl.pathname.startsWith('/api/v1/actors/')) {
		const [, , , , requestedActorId, panel] = requestUrl.pathname.split('/');
		if (![actorId, partialActorId].includes(requestedActorId)) {
			sendError(404, 'not_found', 'mock-actor-404');
			return;
		}
		if (!panel) {
			response.end(
				JSON.stringify({
					data: {
						id: requestedActorId,
						canonical_name:
							requestedActorId === partialActorId
								? 'Partial Signal'
								: 'Midnight Blizzard',
						description: 'Published adversary identity with source-linked evolution.'
					}
				})
			);
			return;
		}
		if (panel === 'aliases') {
			response.end(
				JSON.stringify({
					data: {
						items: [
							{
								id: '70000000-0000-4000-8000-000000000001',
								name: 'APT29',
								source_native_id: 'apt29',
								confidence: 92,
								source
							}
						],
						truncated: false
					}
				})
			);
			return;
		}
		if (panel === 'associations') {
			response.end(
				JSON.stringify({
					data: {
						behaviors: timelineRecord().behaviors,
						techniques: timelineRecord().techniques,
						behaviors_truncated: false,
						techniques_truncated: false
					}
				})
			);
			return;
		}
		if (panel === 'references') {
			if (requestedActorId === partialActorId) {
				sendError(500, 'server_error', 'mock-reference-500');
				return;
			}
			response.end(
				JSON.stringify({
					data: {
						sources: [source],
						evidence: [evidence()],
						sources_truncated: false,
						evidence_truncated: false
					}
				})
			);
			return;
		}
		if (panel === 'timeline') {
			const cursor = requestUrl.searchParams.get('cursor');
			const data = cursor
				? [
						timelineRecord({
							id: '40000000-0000-4000-8000-000000000002',
							title: 'Earlier credential access',
							observed_at: '2026-02-08T08:00:00Z',
							intelligence_type: 'assessed',
							origin: 'watchtower'
						})
					]
				: [timelineRecord()];
			response.end(
				JSON.stringify({
					data,
					page: { limit: 25, next_cursor: cursor ? null : 'opaque-earlier' }
				})
			);
			return;
		}
	}

	if (requestUrl.pathname !== '/api/v1/search') {
		response.statusCode = 404;
		response.end(
			JSON.stringify({
				error: {
					code: 'not_found',
					message: 'Not found.',
					request_id: 'mock-404',
					details: []
				}
			})
		);
		return;
	}

	const query = requestUrl.searchParams.get('q')?.trim() ?? '';
	if (query === 'rate-limited') {
		sendError(429, 'rate_limited', 'mock-429');
		return;
	}
	if (query === 'server-error') {
		sendError(500, 'server_error', 'mock-500');
		return;
	}

	const cursor = requestUrl.searchParams.get('cursor');
	const data =
		query === 'nothing'
			? []
			: query === 'malicious-update.example'
				? [
						searchRecord({
							entity_type: 'indicator',
							id: '21000000-0000-4000-8000-000000000001',
							title: 'malicious-update.example',
							summary: 'Domain used in a targeted malicious update operation.',
							actor_id: null,
							indicator_type: 'domain',
							indicator_value: 'malicious-update.example',
							related_actors: [
								{
									id: actorId,
									canonical_name: 'Midnight Blizzard',
									description:
										'Published adversary identity with source-linked evolution.',
									latest_observed_at: '2026-03-11T10:00:00Z'
								}
							]
						})
					]
				: query === 'CVE-2026-45123'
					? [
							searchRecord({
								entity_type: 'vulnerability',
								id: '22000000-0000-4000-8000-000000000001',
								title: 'CVE-2026-45123',
								summary:
									'Published vulnerability linked to actor exploitation activity.',
								actor_id: null,
								external_id: 'CVE-2026-45123',
								severity: 'critical',
								cvss_score: 9.8,
								related_actors: [
									{
										id: actorId,
										canonical_name: 'Midnight Blizzard',
										description:
											'Published adversary identity with source-linked evolution.',
										latest_observed_at: '2026-03-11T10:00:00Z'
									}
								]
							})
						]
					: cursor
						? [
								searchRecord({
									entity_type: 'source',
									id: '20000000-0000-4000-8000-000000000003',
									title: 'Third source result',
									actor_id: null,
									intelligence_type: null,
									origin: null,
									score: 0.25,
									match_kind: 'full_text'
								})
							]
						: [
								searchRecord({}),
								searchRecord({
									entity_type: 'technique',
									id: '20000000-0000-4000-8000-000000000002',
									title: 'PowerShell',
									external_id: 'T1059.001',
									score: 2.5,
									match_kind: 'full_text'
								})
							];
	response.end(
		JSON.stringify({
			query,
			data,
			limit: 25,
			next_cursor: query === 'midnight' && !cursor ? 'opaque-page-2' : null
		})
	);
});

await new Promise((resolve, reject) => {
	mockApi.once('error', reject);
	mockApi.listen(0, host, resolve);
});
const mockAddress = mockApi.address();
if (!mockAddress || typeof mockAddress === 'string') throw new Error('Could not start mock API.');
const mockApiOrigin = `http://${host}:${mockAddress.port}`;

const run = (command, args, options = {}) =>
	spawn(command, args, {
		cwd: process.cwd(),
		stdio: 'inherit',
		...options
	});

const waitForServer = async (server, origin = baseUrl) => {
	for (let attempt = 0; attempt < 100; attempt += 1) {
		if (server.exitCode !== null) {
			throw new Error(`The production server exited with code ${server.exitCode}.`);
		}

		try {
			const response = await fetch(`${origin}/search`);
			if (response.ok) return;
		} catch {
			// The server is still starting.
		}

		await new Promise((resolve) => setTimeout(resolve, 100));
	}

	throw new Error(`The production server did not become ready at ${origin}.`);
};

const waitForExit = (child) =>
	new Promise((resolve, reject) => {
		child.once('error', reject);
		child.once('exit', (code, signal) => resolve({ code, signal }));
	});

const disabledPort = await new Promise((resolve, reject) => {
	const probe = createNetServer();
	probe.once('error', reject);
	probe.listen(0, host, () => {
		const address = probe.address();
		if (!address || typeof address === 'string') {
			probe.close();
			reject(new Error('Could not reserve a local port for the disabled admin check.'));
			return;
		}
		probe.close((error) => (error ? reject(error) : resolve(String(address.port))));
	});
});
const disabledBaseUrl = `http://${host}:${disabledPort}`;
const disabledServer = run(process.execPath, ['build/index.js'], {
	env: {
		...process.env,
		HOST: host,
		PORT: disabledPort,
		ORIGIN: disabledBaseUrl,
		PROTOCOL_HEADER: 'x-forwarded-proto',
		WATCHTOWER_API_ORIGIN: mockApiOrigin,
		WATCHTOWER_ADMIN_ENABLED: 'false',
		WATCHTOWER_OPERATOR_TOKEN: ''
	}
});
const disabledServerExit = waitForExit(disabledServer);
await waitForServer(disabledServer, disabledBaseUrl);
const disabledResponse = await fetch(`${disabledBaseUrl}/admin/integrations`);
if (disabledResponse.status !== 404) {
	throw new Error(`Disabled admin route returned ${disabledResponse.status}; expected 404.`);
}
disabledServer.kill();
await disabledServerExit;

const server = run(process.execPath, ['build/index.js'], {
	env: {
		...process.env,
		HOST: host,
		PORT: port,
		ORIGIN: baseUrl,
		PROTOCOL_HEADER: 'x-forwarded-proto',
		WATCHTOWER_API_ORIGIN: mockApiOrigin,
		WATCHTOWER_ADMIN_ENABLED: 'true',
		WATCHTOWER_OPERATOR_TOKEN: operatorToken
	}
});
const serverExit = waitForExit(server);

let playwrightResult;

try {
	await Promise.race([
		waitForServer(server),
		serverExit.then(({ code, signal }) => {
			throw new Error(
				`The production server exited before testing (code ${code}, signal ${signal}).`
			);
		})
	]);

	const playwright = run(process.execPath, ['node_modules/@playwright/test/cli.js', 'test'], {
		env: {
			...process.env,
			WATCHTOWER_E2E_BASE_URL: baseUrl,
			WATCHTOWER_E2E_FORWARDED_PROTO: 'http'
		}
	});
	playwrightResult = await waitForExit(playwright);
} finally {
	if (server.exitCode === null) {
		server.kill();
		await serverExit.catch(() => undefined);
	}
	mockApi.close();
}

process.exitCode = playwrightResult?.code ?? 1;
