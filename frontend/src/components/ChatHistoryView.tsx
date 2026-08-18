import { useQuery } from '@tanstack/react-query'
import { MessageSquareText, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { getQueryHistory, getApiErrorMessage } from '@/lib/api'

export function ChatHistoryView() {
  const historyQuery = useQuery({ queryKey: ['query-history'], queryFn: () => getQueryHistory() })
  const queries = historyQuery.data?.queries ?? []

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 p-4 md:p-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">History</h2>
        <p className="text-sm text-muted-foreground">Every question you have asked, most recent first.</p>
      </div>

      {historyQuery.isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : historyQuery.isError ? (
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="size-4 text-destructive" />
            <p className="flex-1 text-sm text-muted-foreground">
              {getApiErrorMessage(historyQuery.error)}
            </p>
            <Button variant="outline" size="sm" onClick={() => historyQuery.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : queries.length === 0 ? (
        <Card>
          <CardHeader className="items-center text-center">
            <div className="mb-1 flex size-11 items-center justify-center rounded-lg border bg-card">
              <MessageSquareText className="size-5 text-muted-foreground" />
            </div>
            <CardTitle className="text-base">No questions yet</CardTitle>
            <CardDescription>
              Open a document and ask something. Your questions will collect here.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="space-y-2">
          {queries.map((item) => (
            <Card key={item.id} className="gap-0 py-0">
              <CardContent className="space-y-1.5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium">{item.query}</p>
                  <span className="shrink-0 text-[11px] text-muted-foreground tabular-nums">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>
                {item.response && (
                  <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                    {item.response}
                  </p>
                )}
                {typeof item.response_time === 'number' && (
                  <p className="text-[11px] text-muted-foreground tabular-nums">
                    {item.response_time.toFixed(1)}s
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
