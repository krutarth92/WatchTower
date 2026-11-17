import { describe, expect, it } from 'vitest';
import { parseApiOrigin, privateBoolean, privateEnvironmentLabel } from './api-origin';

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

describe('privateBoolean', () => {
	it('defaults to disabled and accepts explicit booleans', () => {
		expect(privateBoolean('FEATURE', undefined)).toBe(false);
		expect(privateBoolean('FEATURE', ' TRUE ')).toBe(true);
		expect(privateBoolean('FEATURE', 'false')).toBe(false);
	});

	it('rejects ambiguous values', () => {
		expect(() => privateBoolean('FEATURE', 'yes')).toThrow('FEATURE must be true or false');
	});
});
