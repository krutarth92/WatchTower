import { spawn } from 'node:child_process';
import { createServer } from 'node:net';

const host = '127.0.0.1';
const port = await new Promise((resolve, reject) => {
	const probe = createServer();
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
	env: { ...process.env, HOST: host, PORT: port }
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
}

process.exitCode = playwrightResult?.code ?? 1;
