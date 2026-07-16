'use client'

import { EamosSearch } from '@/components/landing/EamosSearch'
import { ModePill } from '@/components/layout/ModePill'
import { RailFoot } from '@/components/layout/RailFoot'
import { TopNav } from '@/components/layout/TopNav'
import { WorkRail } from '@/components/layout/WorkRail'
import { ReportLoadingState } from '@/components/report/ReportLoadingState'
import { SearchInterpretationPanel } from '@/components/report/SearchInterpretationPanel'
import { VariantLibraryRail } from '@/components/report/VariantLibraryRail'

import { ReportAiPanel, ReportBody } from './report-client/ReportBody'
import {
  CenteredMain,
  ErrorBlock,
  MalformedBlock,
} from './report-client/ReportLoadStates'
import { useReportClient } from './report-client/useReportClient'

export function ReportClient() {
  const {
    activeState,
    backHref,
    backLabel,
    cdna,
    fromCompare,
    gene,
    handleSearch,
    handleSelectCandidate,
    lazyOverrides,
    negativeFixture,
    queryLabel,
    retry,
    searchFocused,
    setSearchFocused,
    summaryRequest,
  } = useReportClient()

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <TopNav right={<ModePill current="report" />}>
        <div
          className="mx-auto"
          onFocus={() => setSearchFocused(true)}
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              setSearchFocused(false)
            }
          }}
          style={{
            width: '100%',
            maxWidth: searchFocused ? 760 : 640,
            transition: 'max-width 460ms var(--ease-emphasized)',
          }}
        >
          <EamosSearch size="compact" tone="light" onSubmit={handleSearch} />
        </div>
      </TopNav>

      {activeState.kind === 'ready' ? (
        <WorkRail
          surface="report"
          title="Library"
          aiTitle="Ask Eamos"
          foot={<RailFoot />}
          aiPanel={
            <ReportAiPanel
              data={activeState.data}
              queryFallback={`${gene} ${cdna}`.trim() || activeState.data.query}
            />
          }
          output={
            <CenteredMain bleed>
              <ReportBody
                key={activeState.requestKey}
                data={activeState.data}
                query={`${gene} ${cdna}`.trim() || activeState.data.query}
                summaryRequest={summaryRequest}
                lazyOverrides={lazyOverrides}
                demo={negativeFixture}
              />
            </CenteredMain>
          }
        >
          <VariantLibraryRail
            data={activeState.data}
            query={queryLabel}
            viewMetricsEnabled={!negativeFixture}
          />
        </WorkRail>
      ) : (
        <CenteredMain>
          {activeState.kind === 'loading' && (
            <ReportLoadingState query={queryLabel} gene={gene} cdna={cdna} />
          )}
          {activeState.kind === 'error' && (
            <ErrorBlock
              variant="generic"
              message={activeState.message}
              query={queryLabel}
              onRetry={retry}
              backHref={backHref}
              backLabel={backLabel}
              showDemo={!fromCompare}
            />
          )}
          {activeState.kind === 'offline' && (
            <ErrorBlock
              variant="offline"
              query={queryLabel}
              onRetry={retry}
              backHref={backHref}
              backLabel={backLabel}
              showDemo={!fromCompare}
            />
          )}
          {activeState.kind === 'malformed' && (
            <MalformedBlock
              query={activeState.query}
              detail={activeState.detail}
              backHref={backHref}
              backLabel={backLabel}
              showDemo={!fromCompare}
            />
          )}
          {activeState.kind === 'unresolved' && (
            <ErrorBlock
              variant="unresolved"
              query={activeState.query}
              onRetry={retry}
              backHref={backHref}
              backLabel={backLabel}
              showDemo={!fromCompare}
            />
          )}
          {activeState.kind === 'interpretation' && (
            <SearchInterpretationPanel
              query={activeState.query}
              interpretation={activeState.interpretation}
              limitations={activeState.detail}
              onSelectCandidate={handleSelectCandidate}
            />
          )}
        </CenteredMain>
      )}
    </div>
  )
}
