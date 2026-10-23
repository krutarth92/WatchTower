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

const searchRecord = (overrides) => ({
	entity_type: 'actor',
	id: '20000000-0000-4000-8000-000000000001',
	title: 'Midnight Blizzard',
	summary: 'Published actor intelligence from the deterministic test API.',
	source_id: '10000000-0000-4000-8000-000000000001',
	actor_id: '20000000-0000-4000-8000-000000000001',
	external_id: null,
	observed_at: '2026-01-02T03:04:05Z',
	intelligence_type: 'observed',
	origin: 'imported',
	match_kind: 'exact',
	score: 100.25,
	...overrides
});

const mockApi = createHttpServer((request, response) => {
	const requestUrl = new URL(request.url ?? '/', 'http://mock-api');
	response.setHeader('content-type', 'application/json');
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
		response.statusCode = 429;
		response.end(
			JSON.stringify({
				error: {
					code: 'rate_limited',
					message: 'Mock detail.',
					request_id: 'mock-429',
					details: []
				}
			})
		);
		return;
	}
	if (query === 'server-error') {
		response.statusCode = 500;
		response.end(
			JSON.stringify({
				error: {
					code: 'server_error',
					message: 'Mock detail.',
					request_id: 'mock-500',
					details: []
				}
			})
		);
		return;
	}

	const cursor = requestUrl.searchParams.get('cursor');
	const data =
		query === 'nothing'
			? []
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
			next_cursor: query !== 'nothing' && !cursor ? 'opaque-page-2' : null
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
