import { describe, expect, it } from 'vitest';
import { parseApiOrigin, privateEnvironmentLabel } from './api-origin';

describe('parseApiOrigin', () => {
	it('uses the loopback development origin by default', () => {
		expect(parseApiOrigin(undefined)).toBe('http://127.0.0.1:8000');
	});

	it.each(['https://api.watchtower.test', 'http://localhost:8100'])(
		'accepts the safe origin %s',
		(origin) => {
			expect(parseApiOrigin(origin)).toBe(origin);
		}
	);

	it.each([
		'file:///tmp/watchtower',
		'javascript:alert(1)',
		'https://user:secret@example.test',
		'https://example.test/api',
		'https://example.test?target=elsewhere',
		'https://example.test/#fragment'
	])('rejects unsafe origin input %s', (origin) => {
		expect(() => parseApiOrigin(origin)).toThrow();
	});
});

describe('privateEnvironmentLabel', () => {
	it('never exposes an arbitrary environment value', () => {
		expect(privateEnvironmentLabel('customer-secret')).toBe('LOCAL / PRIVATE');
	});
});
