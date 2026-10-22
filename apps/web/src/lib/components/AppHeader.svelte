<script lang="ts">
	let {
		environmentLabel,
		currentPath
	}: {
		environmentLabel: string;
		currentPath: string;
	} = $props();

	const researchActive = $derived(currentPath === '/search' || currentPath.startsWith('/actors/'));
</script>

<header class="app-header">
	<div class="header-inner">
		<a class="brand" href="/search">
			<span class="mark-frame">
				<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
					<path d="M6 27h20M9 27V13l7-8 7 8v14M12 14h8M13 19h6M16 14v13" />
				</svg>
			</span>
			<span class="brand-copy">
				<span class="wordmark">WATCH<span class="brand-accent">TOWER</span></span>
				<span class="brand-subtitle">INTELLIGENCE OPERATIONS</span>
			</span>
		</a>

		<nav aria-label="Primary navigation">
			<a
				class:active={researchActive}
				aria-current={researchActive ? 'page' : undefined}
				href="/search"
			>
				<span class="nav-index" aria-hidden="true">01</span> Research
			</a>
			<span class="nav-pending" aria-disabled="true"
				><span class="nav-index" aria-hidden="true">02</span> Advisories</span
			>
		</nav>

		<span class="environment-label"><span aria-hidden="true"></span>{environmentLabel}</span>
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
		display: flex;
		min-height: var(--header-height);
		max-width: var(--content-width);
		align-items: center;
		gap: var(--space-6);
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
	}

	.mark-frame {
		display: grid;
		width: 2.25rem;
		height: 2.25rem;
		place-items: center;
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-sm);
		background: var(--gradient-surface), var(--color-surface);
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

	.brand-copy {
		display: grid;
		line-height: 1;
	}

	.wordmark {
		font-size: var(--font-size-sm);
	}

	.brand-subtitle {
		margin-top: var(--space-1);
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: 0.5625rem;
		font-weight: 500;
		letter-spacing: 0.12em;
	}

	.brand-accent {
		color: var(--color-primary);
	}

	nav {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		margin-left: auto;
		font-size: var(--font-size-sm);
	}

	nav a,
	.nav-pending {
		position: relative;
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-sm);
		color: var(--color-ink-muted);
		text-decoration: none;
		transition:
			color var(--motion-fast) var(--easing-standard),
			background var(--motion-fast) var(--easing-standard);
	}

	.nav-index {
		margin-right: var(--space-1);
		font-family: var(--font-mono);
		font-size: 0.625rem;
		opacity: 0.72;
	}

	nav a:hover,
	nav a.active {
		background: var(--color-primary-soft);
		color: var(--color-primary);
	}

	nav a.active::after {
		position: absolute;
		right: var(--space-3);
		bottom: 0;
		left: var(--space-3);
		height: var(--border-width);
		background: var(--gradient-brand);
		content: '';
	}

	.nav-pending {
		cursor: not-allowed;
		opacity: 0.66;
	}

	.environment-label {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-2);
		border: var(--border-width) solid var(--color-observed);
		border-radius: var(--radius-sm);
		color: var(--color-observed);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	.environment-label span {
		width: 0.375rem;
		height: 0.375rem;
		border-radius: 50%;
		background: currentColor;
		box-shadow: 0 0 var(--space-2) currentColor;
	}

	@media (max-width: 40rem) {
		.header-inner {
			flex-wrap: wrap;
			gap: var(--space-2) var(--space-4);
			padding-block: var(--space-3);
		}

		nav {
			order: 3;
			width: 100%;
			margin-left: 0;
		}

		.environment-label {
			margin-left: auto;
		}
	}

	@media (max-width: 55rem) {
		.brand-subtitle {
			display: none;
		}
	}
</style>
