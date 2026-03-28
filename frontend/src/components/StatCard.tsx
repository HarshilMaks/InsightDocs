import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string
  description: string
  icon: LucideIcon
  tone?: 'primary' | 'sky' | 'emerald' | 'amber'
}

const toneClasses: Record<NonNullable<StatCardProps['tone']>, string> = {
  primary: 'from-primary/15 to-primary-container/20 text-primary',
  sky: 'from-sky-500/15 to-sky-500/20 text-sky-300',
  emerald: 'from-emerald-500/15 to-emerald-500/20 text-emerald-300',
  amber: 'from-amber-500/15 to-amber-500/20 text-amber-300',
}

export function StatCard({ label, value, description, icon: Icon, tone = 'primary' }: StatCardProps) {
  return (
    <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-low/80 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">{label}</p>
          <p className="mt-2 text-3xl font-semibold text-on-surface">{value}</p>
        </div>
        <div
          className={cn(
            'flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br',
            toneClasses[tone],
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-4 text-sm text-on-surface-variant">{description}</p>
    </div>
  )
}
