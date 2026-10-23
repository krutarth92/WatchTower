<script lang="ts">
	import { navigating } from '$app/state';
	import type { PageProps } from './$types';
	import type {
		AliasResponse,
		AssociationResponse,
		ReferenceResponse,
		TimelineEvent,
		TimelinePageResponse
	} from '#lib/api/contracts.ts';
	import { serializeActorWorkspaceState } from '#lib/actors/state.ts';
	import type { ActorPanel } from '#lib/server/actors/page.ts';
	import ActorTimelineEvent from '#lib/components/ActorTimelineEvent.svelte';
	import EvidenceDisclosure from '#lib/components/EvidenceDisclosure.svelte';
	import SafeLocator from '#lib/components/SafeLocator.svelte';
	import StatePanel from '#lib/components/StatePanel.svelte';

	type PanelName = 'aliases' | 'associations' | 'timeline' | 'references';
	type PanelError = { status: number; message: string; requestId: string | null };
	type PanelResponse<T> = { data: T } | { error: PanelError };

	let { data }: PageProps = $props();
	let aliasesPanel = $state<ActorPanel<AliasResponse['data']> | null>(null);
	let associationsPanel = $state<ActorPanel<AssociationResponse['data']> | null>(null);
	let timelinePanel = $state<ActorPanel<TimelinePageResponse> | null>(null);
	let referencesPanel = $state<ActorPanel<ReferenceResponse['data']> | null>(null);
	let timelineEvents = $state<TimelineEvent[]>([]);
	let nextCursor = $state<string | null>(null);
	let retrying = $state<Record<PanelName, boolean>>({
		aliases: false,
		associations: false,
		timeline: false,
		references: false
	});
	let pageError = $state<PanelError | null>(null);

	const actorId = $derived(data.actor?.id ?? '');
	const workspaceState = $derived(data.workspace.state);
	const workspaceQuery = $derived(serializeActorWorkspaceState(workspaceState).toString());
	const hasTimelineFilters = $derived(
		Boolean(workspaceState.dateFrom || workspaceState.dateTo || workspaceState.intelligenceType)
	);
	const isNavigating = $derived(Boolean(navigating.to));

	$effect(() => {
		aliasesPanel = data.panels.aliases;
		associationsPanel = data.panels.associations;
		timelinePanel = data.panels.timeline;
		referencesPanel = data.panels.references;
		timelineEvents =
			data.panels.timeline?.state === 'success' ? [...data.panels.timeline.data.data] : [];
		nextCursor =
			data.panels.timeline?.state === 'success' ? data.panels.timeline.data.page.next_cursor : null;
		pageError = null;
		retrying = { aliases: false, associations: false, timeline: false, references: false };
	});

	function panelEndpoint(panel: PanelName) {
		return `/actors/${actorId}/panels/${panel}${workspaceQuery ? `?${workspaceQuery}` : ''}`;
	}

	async function requestPanel<T>(panel: PanelName, cursor?: string): Promise<PanelResponse<T>> {
		try {
			const response = await fetch(panelEndpoint(panel), {
				method: 'POST',
				headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
				body: JSON.stringify(cursor ? { cursor } : {})
			});
			const body = (await response.json()) as PanelResponse<T>;
			if (!response.ok && !('error' in body)) {
				return {
					error: {
						status: response.status,
						message: 'This section is unavailable. Retry this section.',
						requestId: null
					}
				};
			}
			return body;
		} catch {
			return {
				error: {
					status: 0,
					message: 'This section is unavailable. Retry this section.',
					requestId: null
				}
			};
		}
	}

	async function retryPanel(panel: PanelName) {
		if (!actorId || retrying[panel]) return;
		retrying = { ...retrying, [panel]: true };
		if (panel === 'aliases') {
			const response = await requestPanel<AliasResponse['data']>(panel);
			aliasesPanel =
				'data' in response
					? { state: 'success', data: response.data }
					: { state: 'error', error: response.error };
		} else if (panel === 'associations') {
			const response = await requestPanel<AssociationResponse['data']>(panel);
			associationsPanel =
				'data' in response
					? { state: 'success', data: response.data }
					: { state: 'error', error: response.error };
		} else if (panel === 'references') {
			const response = await requestPanel<ReferenceResponse['data']>(panel);
			referencesPanel =
				'data' in response
					? { state: 'success', data: response.data }
					: { state: 'error', error: response.error };
		} else {
			const response = await requestPanel<TimelinePageResponse>(panel);
			timelinePanel =
				'data' in response
					? { state: 'success', data: response.data }
					: { state: 'error', error: response.error };
			if ('data' in response) {
				timelineEvents = [...response.data.data];
				nextCursor = response.data.page.next_cursor;
			}
		}
		retrying = { ...retrying, [panel]: false };
	}

	async function loadEarlier() {
		if (!nextCursor || retrying.timeline) return;
		retrying = { ...retrying, timeline: true };
		pageError = null;
		const response = await requestPanel<TimelinePageResponse>('timeline', nextCursor);
		if ('error' in response) {
			pageError = response.error;
		} else {
			timelineEvents = [...timelineEvents, ...response.data.data];
			nextCursor = response.data.page.next_cursor;
		}
		retrying = { ...retrying, timeline: false };
	}

	function retryPage() {
		window.location.reload();
	}
</script>

<svelte:head>
	<title>{data.actor?.canonical_name ?? 'Actor unavailable'} | WATCHTOWER</title>
	<meta
		name="description"
		content="Published actor identity, behavior, evolution, provenance and evidence."
	/>
</svelte:head>

<section class="actor-workspace" aria-labelledby="actor-title">
	<div class="workspace-inner">
		{#if data.view === 'invalid'}
			<a class="back-link" href="/search">← Return to research search</a>
			<div class="route-state" id="actor-title">
				<StatePanel
					state="error"
					title="Actor request unavailable"
					message={data.workspace.errors.join(' ')}
				/>
			</div>
		{:else if data.view === 'unavailable'}
			<a class="back-link" href={workspaceState.fromSearch}>← Return to research search</a>
			<div class="route-state" id="actor-title">
				<StatePanel
					state="error"
					title="Published actor unavailable"
					message={data.actorError?.message ?? 'This published record is unavailable.'}
					requestId={data.actorError?.requestId ?? undefined}
					onRetry={retryPage}
				/>
			</div>
		{:else if data.actor}
			<a class="back-link" href={workspaceState.fromSearch}>← Back to research results</a>
			<header class="actor-header">
				<div class="identity-mark" aria-hidden="true"><span></span><span></span></div>
				<div class="identity-copy">
					<p>PUBLISHED ACTOR DOSSIER</p>
					<h1 id="actor-title">{data.actor.canonical_name}</h1>
					{#if data.actor.description}<p class="description">{data.actor.description}</p>{/if}
					<code>{data.actor.id}</code>
				</div>
				<div class="visibility"><span aria-hidden="true"></span>PUBLISHED ONLY</div>
			</header>

			<section class="alias-strip" aria-labelledby="aliases-title" aria-busy={retrying.aliases}>
				<div class="section-heading">
					<div>
						<span>IDENTITY / 01</span>
						<h2 id="aliases-title">Known aliases</h2>
					</div>
					<small>Source-preserved names</small>
				</div>
				{#if aliasesPanel?.state === 'error'}
					<StatePanel
						state="error"
						title="Aliases unavailable"
						message={aliasesPanel.error.message}
						requestId={aliasesPanel.error.requestId ?? undefined}
						onRetry={() => retryPanel('aliases')}
					/>
				{:else if aliasesPanel?.state === 'success'}
					{#if aliasesPanel.data.items.length}
						<ul class="alias-list">
							{#each aliasesPanel.data.items as alias (alias.id)}
								<li>
									<strong>{alias.name}</strong><span>{alias.source.name}</span>
									{#if alias.confidence !== null}<small>{alias.confidence}% confidence</small>{/if}
								</li>
							{/each}
						</ul>
					{:else}<p class="quiet">No published aliases.</p>{/if}
					{#if aliasesPanel.data.truncated}<p class="truncated">
							Additional aliases are available through the API.
						</p>{/if}
				{/if}
			</section>

			<div class="workspace-grid">
				<div class="primary-workspace">
					<section
						class="association-section"
						aria-labelledby="association-title"
						aria-busy={retrying.associations}
					>
						<div class="section-heading">
							<div>
								<span>BEHAVIOR / 02</span>
								<h2 id="association-title">Observed associations</h2>
							</div>
							<small>No inferred relationships</small>
						</div>
						{#if associationsPanel?.state === 'error'}
							<StatePanel
								state="error"
								title="Associations unavailable"
								message={associationsPanel.error.message}
								requestId={associationsPanel.error.requestId ?? undefined}
								onRetry={() => retryPanel('associations')}
							/>
						{:else if associationsPanel?.state === 'success'}
							<div class="association-groups">
								<div>
									<h3>Behaviors</h3>
									{#if associationsPanel.data.behaviors.length}<ul>
											{#each associationsPanel.data.behaviors as behavior (behavior.id)}<li>
													{behavior.name}
												</li>{/each}
										</ul>{:else}<p class="quiet">No published behavior associations.</p>{/if}
									{#if associationsPanel.data.behaviors_truncated}<p class="truncated">
											Additional behaviors are available through the API.
										</p>{/if}
								</div>
								<div>
									<h3>Techniques</h3>
									{#if associationsPanel.data.techniques.length}<ul>
											{#each associationsPanel.data.techniques as technique (technique.id)}
												<li><code>{technique.external_id}</code> {technique.name}</li>
											{/each}
										</ul>{:else}<p class="quiet">No published technique associations.</p>{/if}
									{#if associationsPanel.data.techniques_truncated}<p class="truncated">
											Additional techniques are available through the API.
										</p>{/if}
								</div>
							</div>
						{/if}
					</section>

					<section
						class="timeline-section"
						aria-labelledby="timeline-title"
						aria-busy={isNavigating || retrying.timeline}
					>
						<div class="section-heading timeline-heading">
							<div>
								<span>EVOLUTION / 03</span>
								<h2 id="timeline-title">Published timeline</h2>
							</div>
							<small>Newest to oldest / API order</small>
						</div>

						<form
							class="timeline-filters"
							method="GET"
							action={`/actors/${actorId}`}
							aria-label="Timeline filters"
						>
							<label
								><span>From UTC</span><input
									type="date"
									name="date_from"
									value={workspaceState.dateFrom}
								/></label
							>
							<label
								><span>To UTC</span><input
									type="date"
									name="date_to"
									value={workspaceState.dateTo}
								/></label
							>
							<label
								><span>Intelligence</span><select
									name="intelligence_type"
									value={workspaceState.intelligenceType}
								>
									<option value="">Observed + assessed</option><option value="observed"
										>Observed</option
									><option value="assessed">Assessed</option>
								</select></label
							>
							{#if workspaceState.fromSearch !== '/search'}<input
									type="hidden"
									name="fromSearch"
									value={workspaceState.fromSearch}
								/>{/if}
							<button type="submit">Apply scope</button>
							{#if hasTimelineFilters}<a
									href={`/actors/${actorId}?${new URLSearchParams(workspaceState.fromSearch !== '/search' ? { fromSearch: workspaceState.fromSearch } : {}).toString()}`.replace(
										/\?$/,
										''
									)}>Clear timeline scope</a
								>{/if}
						</form>

						{#if isNavigating && timelineEvents.length}<p class="stale">
								Updating scope. Current events remain visible and may be stale.
							</p>{/if}
						{#if timelinePanel?.state === 'error'}
							<StatePanel
								state="error"
								title="Timeline unavailable"
								message={timelinePanel.error.message}
								requestId={timelinePanel.error.requestId ?? undefined}
								onRetry={() => retryPanel('timeline')}
							/>
						{:else if timelinePanel?.state === 'success' && !timelineEvents.length}
							<StatePanel
								state="empty"
								title="No published events match this scope"
								message="Keep the actor identity visible and broaden or clear the timeline filters."
							/>
						{:else if timelinePanel?.state === 'success'}
							<div class="timeline-list">
								{#each timelineEvents as event (event.id)}<ActorTimelineEvent {event} />{/each}
							</div>
							{#if pageError}<div class="page-error" role="alert">
									<div>
										<strong>CURRENT EVENTS RETAINED</strong><span>{pageError.message}</span
										>{#if pageError.requestId}<code>REQUEST {pageError.requestId}</code>{/if}
									</div>
									<button type="button" onclick={loadEarlier}>Retry page</button>
								</div>{/if}
							{#if nextCursor}<div class="load-earlier">
									<button type="button" onclick={loadEarlier} disabled={retrying.timeline}
										>{retrying.timeline ? 'Loading earlier events…' : 'Load earlier events'}</button
									><span>CURSOR REMAINS OPAQUE</span>
								</div>{:else}<p class="end-marker">— EARLIEST PUBLISHED EVENT LOADED —</p>{/if}
						{/if}
					</section>
				</div>

				<aside
					class="reference-rail"
					aria-labelledby="references-title"
					aria-busy={retrying.references}
				>
					<div class="section-heading">
						<div>
							<span>CONTEXT / 04</span>
							<h2 id="references-title">Reference rail</h2>
						</div>
					</div>
					{#if referencesPanel?.state === 'error'}
						<StatePanel
							state="error"
							title="References unavailable"
							message={referencesPanel.error.message}
							requestId={referencesPanel.error.requestId ?? undefined}
							onRetry={() => retryPanel('references')}
						/>
					{:else if referencesPanel?.state === 'success'}
						<section class="source-list" aria-labelledby="source-list-title">
							<h3 id="source-list-title">Sources</h3>
							{#if referencesPanel.data.sources.length}<ul>
									{#each referencesPanel.data.sources as source (source.id)}<li>
											<strong>{source.name}</strong><span>{source.kind}</span><SafeLocator
												value={source.base_url}
												label="Source home"
											/>
										</li>{/each}
								</ul>{:else}<p class="quiet">No published source references.</p>{/if}
							{#if referencesPanel.data.sources_truncated}<p class="truncated">
									Additional sources are available through the API.
								</p>{/if}
						</section>
						<section class="reference-evidence" aria-labelledby="reference-evidence-title">
							<h3 id="reference-evidence-title">Evidence index</h3>
							{#if referencesPanel.data.evidence.length}<div>
									{#each referencesPanel.data.evidence as evidence (evidence.id)}<EvidenceDisclosure
											{evidence}
										/>{/each}
								</div>{:else}<p class="quiet">No published evidence references.</p>{/if}
							{#if referencesPanel.data.evidence_truncated}<p class="truncated">
									Additional evidence is available through the API.
								</p>{/if}
						</section>
					{/if}
				</aside>
			</div>
		{/if}
	</div>
</section>

<style>
	.actor-workspace {
		position: relative;
		min-height: calc(100vh - var(--header-height));
		background-color: var(--color-canvas);
		background-image: var(--gradient-ambient), var(--texture-grid);
		background-size:
			auto,
			var(--grid-size) var(--grid-size);
	}
	.actor-workspace::before {
		position: absolute;
		inset: 0 0 auto;
		height: var(--border-width);
		background: var(--gradient-brand);
		content: '';
	}
	.workspace-inner {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: var(--space-6) var(--space-5) var(--space-8);
	}
	.back-link {
		display: inline-block;
		margin-bottom: var(--space-5);
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
		text-decoration: none;
	}
	.actor-header {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--space-5);
		padding-bottom: var(--space-7);
		border-bottom: var(--border-width) solid var(--color-border-strong);
	}
	.identity-mark {
		position: relative;
		width: 5rem;
		height: 5rem;
		transform: rotate(45deg);
	}
	.identity-mark::before,
	.identity-mark::after,
	.identity-mark span {
		position: absolute;
		content: '';
		background: var(--color-primary);
	}
	.identity-mark::before {
		top: 50%;
		width: 100%;
		height: var(--border-width);
	}
	.identity-mark::after {
		left: 50%;
		width: var(--border-width);
		height: 100%;
	}
	.identity-mark span:first-child {
		inset: 32%;
		border-radius: 50%;
		background: transparent;
		border: var(--border-width) solid var(--color-secondary);
		box-shadow: 0 0 var(--space-4) var(--color-secondary-faint);
	}
	.identity-mark span:last-child {
		top: calc(50% - var(--space-1));
		left: calc(50% - var(--space-1));
		width: var(--space-2);
		height: var(--space-2);
		border-radius: 50%;
		box-shadow: 0 0 var(--space-3) var(--color-primary-glow);
	}
	.identity-copy > p:first-child,
	.section-heading span,
	.section-heading small,
	.visibility,
	.timeline-filters span,
	.truncated,
	.stale,
	.load-earlier span,
	.end-marker,
	.page-error strong,
	.page-error code {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}
	.identity-copy > p:first-child,
	.section-heading span {
		margin: 0;
		color: var(--color-primary);
		font-weight: 700;
	}
	h1 {
		margin: var(--space-1) 0 var(--space-2);
		font-size: clamp(2.25rem, 6vw, 4.75rem);
		line-height: 0.95;
		letter-spacing: -0.045em;
	}
	.description {
		max-width: 48rem;
		margin: 0 0 var(--space-3);
		color: var(--color-ink-muted);
		font-size: var(--font-size-lg);
	}
	.identity-copy > code {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		overflow-wrap: anywhere;
	}
	.visibility {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-observed);
	}
	.visibility span {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: currentColor;
		box-shadow: 0 0 var(--space-3) currentColor;
	}
	.alias-strip,
	.association-section,
	.timeline-section,
	.reference-rail {
		padding-top: var(--space-5);
	}
	.alias-strip,
	.association-section {
		padding-bottom: var(--space-5);
		border-bottom: var(--border-width) solid var(--color-border-strong);
	}
	.section-heading {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--space-4);
		margin-bottom: var(--space-4);
	}
	.section-heading h2 {
		margin: var(--space-1) 0 0;
		font-size: clamp(1.35rem, 3vw, 2rem);
	}
	.section-heading small {
		color: var(--color-ink-subtle);
	}
	.alias-list,
	.association-groups ul,
	.source-list ul {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.alias-list li {
		display: grid;
		gap: var(--space-1);
		min-width: 11rem;
		padding-left: var(--space-3);
		border-left: 0.125rem solid var(--color-secondary);
	}
	.alias-list span,
	.alias-list small,
	.source-list span {
		color: var(--color-ink-subtle);
		font-size: var(--font-size-xs);
	}
	.workspace-grid {
		display: grid;
		grid-template-columns: minmax(0, 2fr) minmax(18rem, 0.85fr);
		gap: var(--space-7);
	}
	.association-groups {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--space-6);
	}
	.association-groups h3,
	.source-list h3,
	.reference-evidence h3 {
		margin: 0 0 var(--space-3);
		font-size: var(--font-size-base);
	}
	.association-groups li {
		padding: var(--space-2) var(--space-3);
		border-left: 0.125rem solid var(--color-secondary);
		background: var(--color-secondary-faint);
		color: var(--color-ink-muted);
	}
	.association-groups code {
		color: var(--color-secondary);
	}
	.timeline-section {
		padding-top: var(--space-7);
	}
	.timeline-filters {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
		align-items: end;
		gap: var(--space-3);
		margin-bottom: var(--space-6);
		padding: var(--space-3) 0 var(--space-4);
		border-top: var(--border-width) solid var(--color-border);
		border-bottom: var(--border-width) solid var(--color-border);
	}
	.timeline-filters label {
		display: grid;
		gap: var(--space-2);
	}
	.timeline-filters span {
		color: var(--color-ink-subtle);
	}
	.timeline-filters input,
	.timeline-filters select {
		width: 100%;
		min-height: 2.75rem;
		padding: var(--space-2) var(--space-3);
		border: 0;
		border-bottom: var(--border-width) solid var(--color-border-strong);
		background: transparent;
		color: var(--color-ink);
	}
	.timeline-filters button,
	.load-earlier button,
	.page-error button {
		min-height: 2.75rem;
		padding: var(--space-2) var(--space-4);
		border: var(--border-width) solid var(--color-primary);
		border-radius: var(--radius-sm);
		background: var(--color-primary-soft);
		color: var(--color-primary);
		cursor: pointer;
		font-family: var(--font-mono);
		font-weight: 700;
		text-transform: uppercase;
	}
	.timeline-filters a {
		grid-column: 1 / -1;
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}
	.stale {
		margin: 0 0 var(--space-5);
		padding-left: var(--space-3);
		border-left: 0.1875rem solid var(--color-assessed);
		color: var(--color-assessed);
	}
	.timeline-list {
		display: grid;
	}
	.load-earlier {
		display: grid;
		place-items: center;
		gap: var(--space-2);
		padding-top: var(--space-2);
	}
	.load-earlier button {
		min-width: min(100%, 18rem);
	}
	.load-earlier span,
	.end-marker {
		color: var(--color-ink-subtle);
	}
	.end-marker {
		margin: 0;
		text-align: center;
	}
	.page-error {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		margin: 0 0 var(--space-5);
		padding: var(--space-4);
		border-left: 0.1875rem solid var(--color-critical);
	}
	.page-error div {
		display: grid;
		gap: var(--space-1);
	}
	.page-error strong {
		color: var(--color-critical);
	}
	.page-error span {
		color: var(--color-ink-muted);
	}
	.page-error code {
		color: var(--color-ink-subtle);
	}
	.reference-rail {
		align-self: start;
		padding-left: var(--space-6);
		border-left: var(--border-width) solid var(--color-border-strong);
	}
	.source-list,
	.reference-evidence {
		padding: var(--space-4) 0;
		border-top: var(--border-width) solid var(--color-border);
	}
	.source-list ul {
		display: grid;
	}
	.source-list li {
		display: grid;
		gap: var(--space-1);
		padding-left: var(--space-3);
		border-left: 0.125rem solid var(--color-primary);
	}
	.reference-evidence > div {
		display: grid;
		gap: var(--space-2);
	}
	.quiet {
		margin: 0;
		color: var(--color-ink-muted);
	}
	.truncated {
		margin: var(--space-3) 0 0;
		color: var(--color-assessed);
	}
	.route-state {
		padding-top: var(--space-6);
	}
	@media (max-width: 62rem) {
		.workspace-grid {
			grid-template-columns: 1fr;
		}
		.reference-rail {
			padding-left: 0;
			border-top: var(--border-width) solid var(--color-border-strong);
			border-left: 0;
		}
		.timeline-filters {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 40rem) {
		.workspace-inner {
			padding: var(--space-5) var(--space-4) var(--space-8);
		}
		.actor-header {
			grid-template-columns: auto 1fr;
			align-items: start;
		}
		.identity-mark {
			width: 3rem;
			height: 3rem;
		}
		.visibility {
			grid-column: 1 / -1;
		}
		.association-groups,
		.timeline-filters {
			grid-template-columns: 1fr;
		}
		.section-heading,
		.page-error {
			align-items: flex-start;
			flex-direction: column;
		}
	}
</style>
