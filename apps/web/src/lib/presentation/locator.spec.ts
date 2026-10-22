import { describe, expect, it } from 'vitest';
import { safeHttpLocator } from './locator.ts';

describe('safeHttpLocator', () => {
	it.each(['https://example.test/report?id=7', 'http://127.0.0.1:8000/source'])(
		'allows %s',
		(value) => {
			expect(safeHttpLocator(value)?.href).toBe(value);
		}
	);

	it.each([
		'javascript:alert(1)',
		'data:text/html,unsafe',
		'file:///secret',
		'/relative',
		'not a url'
	])('rejects %s', (value) => {
		expect(safeHttpLocator(value)).toBeNull();
	});
});
