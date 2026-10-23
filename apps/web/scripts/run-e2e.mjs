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

const actorId = '20000000-0000-4000-8000-000000000001';
const partialActorId = '20000000-0000-4000-8000-000000000099';
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

const mockApi = createHttpServer((request, response) => {
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

const waitForServer = async (server) => {
	for (let attempt = 0; attempt < 100; attempt += 1) {
		if (server.exitCode !== null) {
			throw new Error(`The production server exited with code ${server.exitCode}.`);
		}

		try {
			const response = await fetch(`${baseUrl}/search`);
			if (response.ok) return;
		} catch {
			// The server is still starting.
		}

		await new Promise((resolve) => setTimeout(resolve, 100));
	}

	throw new Error(`The production server did not become ready at ${baseUrl}.`);
};

const waitForExit = (child) =>
	new Promise((resolve, reject) => {
		child.once('error', reject);
		child.once('exit', (code, signal) => resolve({ code, signal }));
	});

const server = run(process.execPath, ['build/index.js'], {
	env: { ...process.env, HOST: host, PORT: port, WATCHTOWER_API_ORIGIN: mockApiOrigin }
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
		env: { ...process.env, WATCHTOWER_E2E_BASE_URL: baseUrl }
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
