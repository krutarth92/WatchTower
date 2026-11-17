<script lang="ts">
	import { primaryNavigation } from '#lib/site/content.ts';

	let {
		environmentLabel,
		currentPath
	}: {
		environmentLabel: string;
		currentPath: string;
	} = $props();
</script>

<header class="app-header">
	<div class="header-inner">
		<a class="brand" href="/" aria-label="WATCHTOWER home">
			<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
				<path d="M6 27h20M9 27V13l7-8 7 8v14M12 14h8M13 19h6M16 14v13" />
			</svg>
			<span class="wordmark">WATCH<span> TOWER</span></span>
		</a>

		<nav aria-label="Primary navigation">
			{#each primaryNavigation as destination (destination.href)}
				<a
					class:active={destination.match(currentPath)}
					aria-current={destination.match(currentPath) ? 'page' : undefined}
					href={destination.href}
				>
					{destination.label}
				</a>
			{/each}
		</nav>

		<div class="header-meta">
			<a
				class:active={currentPath.startsWith('/updates')}
				href="/updates"
				aria-label="Platform updates"
			>
				<span aria-hidden="true">↗</span><span class="updates-label">Updates</span>
			</a>
			<span class="environment-label"><span aria-hidden="true"></span>{environmentLabel}</span>
		</div>
	</div>
</header>

<style>
	.app-header {
		position: sticky;
		top: 0;
		z-index: 10;
		min-height: var(--header-height);
		border-bottom: var(--border-width) solid var(--color-border);
		background: var(--color-scrim);
		backdrop-filter: blur(var(--space-3));
	}

	.header-inner {
		display: grid;
		min-height: var(--header-height);
		max-width: var(--content-width);
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--space-5);
		margin: 0 auto;
		padding: 0 var(--space-5);
	}

	.brand {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		font-weight: 800;
		letter-spacing: var(--letter-spacing-label);
		text-decoration: none;
		white-space: nowrap;
	}

	.brand-mark {
		width: var(--space-5);
		height: var(--space-5);
		fill: none;
		stroke: var(--color-primary);
		stroke-linecap: round;
		stroke-linejoin: round;
		stroke-width: 2;
	}

	.wordmark {
		font-size: var(--font-size-sm);
	}

	.wordmark span {
		color: var(--color-primary);
	}

	nav {
		display: flex;
		min-width: 0;
		justify-content: center;
		gap: clamp(var(--space-2), 1.7vw, var(--space-5));
	}

	nav a,
	.header-meta a {
		position: relative;
		display: inline-flex;
		min-height: 2.75rem;
		align-items: center;
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
		text-decoration: none;
		white-space: nowrap;
	}

	nav a:hover,
	nav a.active,
	.header-meta a:hover,
	.header-meta a.active {
		color: var(--color-primary);
	}

	nav a.active::after {
		position: absolute;
		right: 0;
		bottom: 0;
		left: 0;
		height: var(--border-width);
		background: var(--gradient-brand);
		content: '';
	}

	.header-meta {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.header-meta a {
		gap: var(--space-1);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		text-transform: uppercase;
	}

	.environment-label {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-observed);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
		white-space: nowrap;
	}

	.environment-label span {
		width: 0.375rem;
		height: 0.375rem;
		border-radius: 50%;
		background: currentColor;
		box-shadow: 0 0 var(--space-2) currentColor;
	}

	@media (max-width: 62rem) {
		.header-inner {
			grid-template-columns: 1fr auto;
			gap: var(--space-1) var(--space-4);
			padding-block: var(--space-2);
		}

		nav {
			grid-column: 1 / -1;
			grid-row: 2;
			justify-content: flex-start;
			overflow-x: auto;
			scrollbar-width: thin;
		}
	}

	@media (max-width: 34rem) {
		.environment-label,
		.updates-label {
			display: none;
		}

		.header-meta {
			gap: var(--space-2);
		}
	}
</style>
