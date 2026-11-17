<script lang="ts">
	import UtcDate from './UtcDate.svelte';
	import type { PlatformUpdate } from '#lib/site/content.ts';

	let { update }: { update: PlatformUpdate } = $props();
</script>

<aside class="update-rail" aria-label="Latest platform update">
	<div class="update-label"><span aria-hidden="true"></span>{update.label}</div>
	<div class="update-copy">
		<strong>{update.title}</strong>
		<span><UtcDate value={update.publishedAt} /></span>
	</div>
	<a href={update.href}>{update.linkLabel}<span aria-hidden="true"> →</span></a>
	<a class="archive-link" href="/updates">All updates</a>
</aside>

<style>
	.update-rail {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto auto;
		align-items: center;
		gap: var(--space-4);
		padding: var(--space-3) 0;
		border-block: var(--border-width) solid var(--color-border);
	}

	.update-label {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-observed);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
		text-transform: uppercase;
	}

	.update-label span {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 50%;
		background: currentColor;
		box-shadow: 0 0 var(--space-3) currentColor;
	}

	.update-copy {
		display: flex;
		min-width: 0;
		align-items: baseline;
		gap: var(--space-3);
	}

	.update-copy strong {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.update-copy span,
	a {
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}

	a {
		min-height: 2.75rem;
		display: inline-flex;
		align-items: center;
		color: var(--color-primary);
		font-weight: 700;
		text-decoration: none;
	}

	a:hover {
		text-decoration: underline;
		text-underline-offset: var(--space-1);
	}

	.archive-link {
		color: var(--color-ink-muted);
		font-weight: 500;
	}

	@media (max-width: 56rem) {
		.update-rail {
			grid-template-columns: minmax(0, 1fr) auto;
		}

		.update-copy {
			grid-column: 1 / -1;
			grid-row: 2;
			align-items: flex-start;
			flex-direction: column;
			gap: var(--space-1);
		}

		.update-copy strong {
			overflow: visible;
			white-space: normal;
		}

		.update-rail > a:not(.archive-link) {
			grid-column: 1;
		}

		.archive-link {
			grid-column: 2;
			grid-row: 1;
		}
	}

	@media (max-width: 31rem) {
		.update-rail {
			grid-template-columns: 1fr;
		}

		.update-copy,
		.update-rail > a:not(.archive-link),
		.archive-link {
			grid-column: 1;
			grid-row: auto;
		}
	}
</style>
