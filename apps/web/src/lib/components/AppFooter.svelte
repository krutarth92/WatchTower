<script lang="ts">
	import { primaryNavigation } from '#lib/site/content.ts';
</script>

<footer>
	<div class="footer-inner">
		<div>
			<strong>WATCHTOWER</strong>
			<p>Track the adversary. Understand the change.</p>
		</div>
		<nav aria-label="Footer navigation">
			{#each primaryNavigation as destination (destination.href)}
				<a href={destination.href}>{destination.label}</a>
			{/each}
			<a href="/updates">Platform updates</a>
		</nav>
		<p class="boundary">Published intelligence only · local/private V1</p>
	</div>
</footer>

<style>
	footer {
		margin-top: var(--space-8);
		border-top: var(--border-width) solid var(--color-border);
	}

	.footer-inner {
		display: grid;
		max-width: var(--content-width);
		grid-template-columns: minmax(12rem, 1fr) 2fr auto;
		gap: var(--space-6);
		align-items: start;
		margin: 0 auto;
		padding: var(--space-6) var(--space-5);
	}

	strong {
		font-size: var(--font-size-sm);
		letter-spacing: var(--letter-spacing-label);
	}

	p {
		margin: var(--space-1) 0 0;
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}

	nav {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-4);
	}

	a {
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
		text-decoration: none;
	}

	a:hover {
		color: var(--color-primary);
	}

	.boundary {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		text-align: right;
		text-transform: uppercase;
	}

	@media (max-width: 52rem) {
		.footer-inner {
			grid-template-columns: 1fr;
		}

		.boundary {
			text-align: left;
		}
	}
</style>
