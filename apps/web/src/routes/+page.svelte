<script lang="ts">
	import type { PageProps } from './$types';
	import PlatformUpdateRail from '#lib/components/PlatformUpdateRail.svelte';
	import UtcDate from '#lib/components/UtcDate.svelte';
	import { latestPlatformUpdate, primaryNavigation } from '#lib/site/content.ts';

	let { data }: PageProps = $props();

	const actors = $derived(data.discovery?.recent.slice(0, 4) ?? []);
	const leadAdvisory = $derived(data.advisories?.data[0] ?? null);
</script>

<svelte:head>
	<title>WATCHTOWER | Adversary intelligence</title>
	<meta
		name="description"
		content="Track adversaries, understand behavioral change and follow published evidence."
	/>
</svelte:head>

<div class="home-shell">
	<section class="hero" aria-labelledby="home-title">
		<div class="hero-copy">
			<p class="eyebrow">Adversary intelligence, connected</p>
			<h1 id="home-title">Track the adversary.<span>Understand what changed.</span></h1>
			<p class="lede">
				Move from an indicator or CVE to the actors, behavior and evidence that explain why it
				matters.
			</p>

			<form action="/search" method="GET" role="search">
				<label for="home-search">Search the intelligence index</label>
				<div class="search-field">
					<input
						id="home-search"
						type="search"
						name="q"
						minlength="2"
						maxlength="200"
						placeholder="Try an actor, indicator, CVE or technique"
					/>
					<button type="submit">Search intelligence</button>
				</div>
			</form>

			<nav class="hero-links" aria-label="Featured destinations">
				<a href="/advisories">Read latest intelligence</a>
				<a href="/actors">Explore threat actors</a>
			</nav>
		</div>

		<div class="hero-visual">
			<img src="/images/watchtower-hero-v2.png" alt="" />
			<div class="visual-shade" aria-hidden="true"></div>
			{#if leadAdvisory}
				<div class="visual-caption">
					<p>Latest published assessment</p>
					<a href={`/advisories/${leadAdvisory.slug}`}>{leadAdvisory.title}</a>
					<small>Published <UtcDate value={leadAdvisory.published_at} /></small>
				</div>
			{:else}
				<div class="visual-caption">
					<p>Evidence-led research</p>
					<strong>Identity, behavior and change in one view.</strong>
				</div>
			{/if}
		</div>
	</section>

	<div class="research-principles" aria-label="WATCHTOWER research principles">
		<span>Published evidence</span>
		<span>Related actor context</span>
		<span>Historical change</span>
	</div>

	<PlatformUpdateRail update={latestPlatformUpdate} />

	<section class="intelligence-section" aria-labelledby="latest-intelligence-title">
		<header class="section-intro">
			<div>
				<p class="eyebrow">Living intelligence</p>
				<h2 id="latest-intelligence-title">Latest intelligence</h2>
			</div>
			<p>
				Focused analysis that preserves what changed, when it changed and which evidence supports
				it.
			</p>
			<a href="/advisories">Browse all intelligence</a>
		</header>

		<div class="feed-grid">
			<div class="advisory-feed">
				{#if data.advisories?.data.length}
					<ol>
						{#each data.advisories.data as advisory (advisory.id)}
							<li>
								<div class="advisory-meta">
									<span>Analysis</span>
									<small><UtcDate value={advisory.published_at} /></small>
								</div>
								<a class="feed-title" href={`/advisories/${advisory.slug}`}>{advisory.title}</a>
								<p>{advisory.summary}</p>
								<small>
									Revision {advisory.published_revision}
									{#if advisory.latest_update_at}
										· updated <UtcDate value={advisory.latest_update_at} />
									{/if}
								</small>
							</li>
						{/each}
					</ol>
				{:else}
					<p class="empty-feed">
						{data.errors.advisories ?? 'No living intelligence advisories have been published yet.'}
					</p>
				{/if}
			</div>

			<aside class="actor-feed" aria-labelledby="active-actors-title">
				<div class="actor-heading">
					<p class="eyebrow">Recently observed</p>
					<h2 id="active-actors-title">Actors in motion</h2>
					<a href="/actors">Open actor directory</a>
				</div>
				{#if actors.length}
					<ul>
						{#each actors as actor (actor.id)}
							<li>
								<a href={`/actors/${actor.id}?fromSearch=%2F`}>{actor.canonical_name}</a>
								<p>{actor.description ?? 'Published actor profile with linked context.'}</p>
								<small>{actor.published_observation_count} published observations</small>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="empty-feed">
						{data.errors.discovery ?? 'Actor discovery will populate from published observations.'}
					</p>
				{/if}
			</aside>
		</div>
	</section>

	<section class="module-index" aria-labelledby="explore-title">
		<header>
			<p class="eyebrow">Explore the research surface</p>
			<h2 id="explore-title">Explore WATCHTOWER</h2>
		</header>
		<div>
			{#each primaryNavigation as destination (destination.href)}
				<a href={destination.href}>
					<strong>{destination.label}</strong>
					<small>{destination.description}</small>
				</a>
			{/each}
		</div>
	</section>
</div>

<style>
	.home-shell {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: var(--space-5);
	}

	.hero {
		display: grid;
		min-height: min(43rem, calc(100vh - var(--header-height) - var(--space-7)));
		grid-template-columns: minmax(0, 0.94fr) minmax(24rem, 1.06fr);
		overflow: hidden;
		border: var(--border-width) solid var(--color-border);
		border-radius: calc(var(--radius-lg) * 1.8);
		background: var(--color-surface);
		box-shadow: var(--shadow-panel);
	}

	.hero-copy {
		position: relative;
		z-index: 1;
		display: flex;
		align-items: flex-start;
		justify-content: center;
		flex-direction: column;
		padding: clamp(2rem, 5vw, 5rem);
	}

	.eyebrow {
		margin: 0;
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
		text-transform: uppercase;
	}

	h1 {
		max-width: 11ch;
		margin: var(--space-4) 0 var(--space-5);
		font-size: clamp(3rem, 5.7vw, 5.4rem);
		letter-spacing: -0.052em;
		line-height: 0.98;
	}

	h1 span {
		display: block;
		margin-top: var(--space-2);
		color: var(--color-threat);
	}

	.lede {
		max-width: 35rem;
		margin: 0 0 var(--space-6);
		color: var(--color-ink-muted);
		font-size: clamp(1.05rem, 1.5vw, 1.25rem);
	}

	form {
		width: min(100%, 40rem);
	}

	form label {
		display: block;
		margin-bottom: var(--space-2);
		font-size: var(--font-size-sm);
		font-weight: 700;
	}

	.search-field {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: var(--space-2);
		padding: var(--space-2);
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-lg);
		background: var(--color-canvas-soft);
	}

	.search-field:focus-within {
		border-color: var(--color-focus);
		box-shadow: var(--shadow-focus);
	}

	input {
		min-width: 0;
		min-height: 3rem;
		padding: 0 var(--space-3);
		border: 0;
		outline: 0;
		background: transparent;
		color: var(--color-ink);
	}

	input::placeholder {
		color: var(--color-ink-subtle);
	}

	button {
		min-height: 3rem;
		padding: 0 var(--space-5);
		border: 0;
		border-radius: calc(var(--radius-lg) - var(--space-1));
		background: var(--color-primary);
		color: var(--color-canvas);
		font-weight: 800;
		cursor: pointer;
	}

	.hero-links {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-5);
		margin-top: var(--space-5);
	}

	.hero-links a,
	.section-intro a,
	.actor-heading a {
		color: var(--color-ink);
		font-size: var(--font-size-sm);
		font-weight: 700;
		text-decoration-color: var(--color-primary);
		text-underline-offset: var(--space-2);
	}

	.hero-visual {
		position: relative;
		min-height: 34rem;
		overflow: hidden;
		background: var(--color-canvas-soft);
	}

	.hero-visual img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		object-position: 55% center;
	}

	.visual-shade {
		position: absolute;
		inset: 0;
		background: var(--gradient-hero-shade);
	}

	.visual-caption {
		position: absolute;
		right: clamp(1.5rem, 4vw, 3rem);
		bottom: clamp(1.5rem, 4vw, 3rem);
		left: clamp(1.5rem, 4vw, 3rem);
		display: grid;
		gap: var(--space-2);
		max-width: 32rem;
	}

	.visual-caption p {
		margin: 0;
		color: var(--color-threat);
		font-size: var(--font-size-sm);
		font-weight: 700;
		text-transform: uppercase;
	}

	.visual-caption a,
	.visual-caption strong {
		color: var(--color-ink);
		font-family: var(--font-display);
		font-size: clamp(1.35rem, 2.5vw, 2rem);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-heading);
		line-height: 1.15;
		text-decoration: none;
	}

	.visual-caption small {
		color: var(--color-ink-muted);
	}

	.research-principles {
		display: flex;
		align-items: center;
		justify-content: center;
		flex-wrap: wrap;
		gap: var(--space-3) var(--space-7);
		padding: var(--space-5);
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}

	.research-principles span::before {
		margin-right: var(--space-2);
		color: var(--color-observed);
		content: '●';
		font-size: 0.65em;
	}

	.intelligence-section {
		padding: var(--space-8) 0 var(--space-7);
	}

	.section-intro {
		display: grid;
		grid-template-columns: minmax(16rem, 0.8fr) minmax(18rem, 1.1fr) auto;
		align-items: end;
		gap: var(--space-6);
		padding-bottom: var(--space-6);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.section-intro h2,
	.actor-heading h2,
	.module-index h2 {
		margin: var(--space-2) 0 0;
		font-size: clamp(2rem, 4vw, 3.25rem);
		letter-spacing: -0.035em;
		line-height: 1.08;
	}

	.section-intro > p {
		max-width: 35rem;
		margin: 0;
		color: var(--color-ink-muted);
	}

	.feed-grid {
		display: grid;
		grid-template-columns: minmax(0, 1.55fr) minmax(19rem, 0.75fr);
		gap: var(--space-8);
		padding-top: var(--space-6);
	}

	.advisory-feed ol,
	.actor-feed ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.advisory-feed li {
		padding: var(--space-5) 0 var(--space-6);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.advisory-meta {
		display: flex;
		justify-content: space-between;
		gap: var(--space-4);
		margin-bottom: var(--space-3);
	}

	.advisory-meta span {
		color: var(--color-threat);
		font-size: var(--font-size-sm);
		font-weight: 700;
	}

	.feed-title {
		color: var(--color-ink);
		font-family: var(--font-display);
		font-size: clamp(1.5rem, 3.2vw, 2.35rem);
		font-weight: 700;
		letter-spacing: -0.025em;
		line-height: 1.18;
		text-decoration-color: var(--color-border-strong);
		text-underline-offset: var(--space-2);
	}

	.advisory-feed li p,
	.actor-feed li p {
		margin: var(--space-3) 0;
		color: var(--color-ink-muted);
	}

	.advisory-feed small,
	.actor-feed small,
	.advisory-meta small {
		color: var(--color-ink-subtle);
		font-size: var(--font-size-sm);
	}

	.actor-feed {
		padding: var(--space-6);
		border-radius: var(--radius-lg);
		background: var(--color-surface-raised);
	}

	.actor-heading {
		display: grid;
		gap: var(--space-2);
		padding-bottom: var(--space-4);
	}

	.actor-heading h2 {
		font-size: clamp(1.8rem, 3vw, 2.45rem);
	}

	.actor-feed li {
		padding: var(--space-4) 0;
		border-top: var(--border-width) solid var(--color-border);
	}

	.actor-feed li > a {
		color: var(--color-ink);
		font-family: var(--font-display);
		font-size: var(--font-size-lg);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-heading);
	}

	.empty-feed {
		padding: var(--space-6) 0;
		color: var(--color-ink-muted);
	}

	.module-index {
		display: grid;
		grid-template-columns: minmax(16rem, 0.7fr) minmax(0, 1.3fr);
		gap: var(--space-8);
		padding: var(--space-7) 0 var(--space-8);
		border-top: var(--border-width) solid var(--color-border);
	}

	.module-index > div {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0 var(--space-7);
	}

	.module-index a {
		display: grid;
		gap: var(--space-1);
		padding: var(--space-4) 0;
		border-bottom: var(--border-width) solid var(--color-border);
		color: var(--color-ink);
		text-decoration: none;
	}

	.module-index a strong {
		font-family: var(--font-display);
		font-size: var(--font-size-lg);
		letter-spacing: var(--letter-spacing-heading);
	}

	.module-index a small {
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}

	.module-index a:hover strong {
		color: var(--color-primary);
	}

	@media (max-width: 62rem) {
		.hero {
			grid-template-columns: 1fr;
		}

		.hero-visual {
			min-height: 28rem;
		}

		.feed-grid,
		.module-index {
			grid-template-columns: 1fr;
			gap: var(--space-6);
		}

		.section-intro {
			grid-template-columns: 1fr auto;
		}

		.section-intro > p {
			grid-column: 1 / -1;
			grid-row: 2;
		}
	}

	@media (max-width: 40rem) {
		.home-shell {
			padding: var(--space-3);
		}

		.hero {
			border-radius: var(--radius-lg);
		}

		.hero-copy {
			padding: var(--space-6) var(--space-5);
		}

		h1 {
			font-size: clamp(2.7rem, 13vw, 4rem);
		}

		.search-field {
			grid-template-columns: 1fr;
		}

		button {
			width: 100%;
		}

		.hero-visual {
			min-height: 23rem;
		}

		.research-principles {
			align-items: flex-start;
			justify-content: flex-start;
			flex-direction: column;
			gap: var(--space-2);
		}

		.intelligence-section {
			padding-top: var(--space-7);
		}

		.section-intro {
			grid-template-columns: 1fr;
			align-items: start;
		}

		.section-intro > p,
		.section-intro > a {
			grid-column: auto;
			grid-row: auto;
		}

		.actor-feed {
			padding: var(--space-5);
		}

		.module-index > div {
			grid-template-columns: 1fr;
		}
	}
</style>
