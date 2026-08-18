import { Upload, MessageSquareText, ScanSearch, BadgeCheck } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const steps = [
  {
    icon: Upload,
    title: 'Upload a document',
    body: 'PDF, DOCX, PPTX or TXT up to 50 MB. Scanned PDFs are read with OCR. Processing runs in the background and the document becomes ready when indexing finishes.',
  },
  {
    icon: MessageSquareText,
    title: 'Ask a question',
    body: 'Questions are answered only from the document you have open. Retrieval combines dense and sparse search, then reranks the best passages before the answer is written.',
  },
  {
    icon: ScanSearch,
    title: 'Open the evidence',
    body: 'Select any citation to jump to its page. When the source is a PDF with stored coordinates, the exact region is outlined on the page.',
  },
  {
    icon: BadgeCheck,
    title: 'Check each claim',
    body: 'Answers are broken into individual claims and each one is checked against the retrieved passages.',
  },
]

const states = [
  {
    label: 'Supported',
    tone: 'border-[color:var(--success)]/30 text-[color:var(--success)]',
    body: 'The claim is backed by at least one retrieved passage.',
  },
  {
    label: 'Not supported by retrieved evidence',
    tone: 'border-destructive/30 text-destructive',
    body: 'No retrieved passage backs this claim. That does not prove the claim is false, only that this document does not support it. Do not cite it from this source.',
  },
  {
    label: 'Verification unavailable',
    tone: 'text-muted-foreground',
    body: 'The verification step could not run. Treat the answer as unchecked.',
  },
]

export function HelpView() {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 p-4 md:p-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">How InsightDocs works</h2>
        <p className="text-sm text-muted-foreground">
          Answers are grounded in your documents and every claim is checked before you see it.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {steps.map((step) => (
          <Card key={step.title}>
            <CardHeader>
              <div className="mb-1 flex size-9 items-center justify-center rounded-md border bg-card">
                <step.icon className="size-4 text-primary" />
              </div>
              <CardTitle className="text-base">{step.title}</CardTitle>
              <CardDescription className="leading-relaxed">{step.body}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reading verification results</CardTitle>
          <CardDescription>What each label means.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          {states.map((state) => (
            <div key={state.label} className="grid gap-1">
              <Badge variant="outline" className={`w-fit font-normal ${state.tone}`}>
                {state.label}
              </Badge>
              <p className="text-sm leading-relaxed text-muted-foreground">{state.body}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Limits worth knowing</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm leading-relaxed text-muted-foreground">
          <p>Region highlighting needs coordinates from the source. Scanned pages and non-PDF files fall back to page and quoted text.</p>
          <p>Each question is scoped to the document you have open, not your whole library.</p>
          <p>Verification is an extra model call, so answers take slightly longer to appear.</p>
        </CardContent>
      </Card>
    </div>
  )
}
