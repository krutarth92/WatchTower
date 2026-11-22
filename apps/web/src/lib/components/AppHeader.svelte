<script lang="ts">
	import { primaryNavigation } from '#lib/site/content.ts';

	let {
		environmentLabel,
		currentPath,
		adminEnabled = false
	}: {
		environmentLabel: string;
		currentPath: string;
		adminEnabled?: boolean;
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

		<nav class="desktop-navigation" aria-label="Primary navigation">
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
			{#if adminEnabled}
				<a
					class:active={currentPath.startsWith('/admin')}
					href="/admin/integrations"
					aria-label="Admin integrations"
				>
					<span class="admin-label">Admin</span>
				</a>
			{/if}
			<a
				class:active={currentPath.startsWith('/updates')}
				href="/updates"
				aria-label="Platform updates"
			>
				<span class="updates-label">Updates</span>
			</a>
			<span class="environment-label"><span aria-hidden="true"></span>{environmentLabel}</span>
		</div>

		<details class="mobile-navigation">
			<summary>Menu</summary>
			<nav aria-label="Mobile navigation">
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
		</details>
	</div>
</header>

<style>
	.app-header {
		position: sticky;
		top: 0;
		z-index: 10;
		min-height: var(--header-height);
		border-bottom: var(--border-width) solid var(--color-border);
		background: var(--color-header-glass);
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
		font-family: var(--font-display);
		font-weight: 800;
		letter-spacing: 0.045em;
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
		font-size: var(--font-size-lg);
		line-height: 1;
	}

	.wordmark span {
		color: var(--color-threat);
	}

	.desktop-navigation {
		display: flex;
		min-width: 0;
		justify-content: center;
		gap: clamp(var(--space-2), 1.7vw, var(--space-5));
	}

	.desktop-navigation a,
	.mobile-navigation a,
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

	.desktop-navigation a:hover,
	.desktop-navigation a.active,
	.mobile-navigation a:hover,
	.mobile-navigation a.active,
	.header-meta a:hover,
	.header-meta a.active {
		color: var(--color-primary);
	}

	.desktop-navigation a.active::after {
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

	.mobile-navigation {
		display: none;
	}

	.header-meta a {
		gap: var(--space-1);
		font-size: var(--font-size-sm);
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

		.desktop-navigation {
			grid-column: 1 / -1;
			grid-row: 2;
			justify-content: flex-start;
			overflow-x: auto;
			scrollbar-width: thin;
		}
	}

	@media (max-width: 34rem) {
		.environment-label {
			display: none;
		}

		.header-inner {
			grid-template-columns: auto minmax(0, 1fr) auto;
			gap: var(--space-2);
			padding-inline: var(--space-4);
		}

		.desktop-navigation {
			display: none;
		}

		.header-meta {
			justify-self: end;
			gap: var(--space-2);
		}

		.header-meta a {
			font-size: var(--font-size-xs);
		}

		.mobile-navigation {
			position: relative;
			display: block;
		}

		.mobile-navigation summary {
			min-height: 2.5rem;
			padding: var(--space-2) var(--space-3);
			border: var(--border-width) solid var(--color-border-strong);
			border-radius: var(--radius-sm);
			color: var(--color-ink);
			cursor: pointer;
			font-size: var(--font-size-xs);
			font-weight: 700;
			list-style: none;
		}

		.mobile-navigation summary::-webkit-details-marker {
			display: none;
		}

		.mobile-navigation nav {
			position: absolute;
			top: calc(100% + var(--space-2));
			right: 0;
			display: grid;
			width: min(17rem, calc(100vw - 2rem));
			padding: var(--space-3);
			border: var(--border-width) solid var(--color-border-strong);
			border-radius: var(--radius-md);
			background: var(--color-surface-raised);
			box-shadow: var(--shadow-panel);
		}

		.mobile-navigation a {
			padding-inline: var(--space-3);
			border-bottom: var(--border-width) solid var(--color-border);
		}

		.mobile-navigation a:last-child {
			border-bottom: 0;
		}
	}
</style>
