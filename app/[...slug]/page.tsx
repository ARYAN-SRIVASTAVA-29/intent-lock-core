import { CatalogPage, DetailPage, PolicyPage, PublicHome, Shell, TransactionsPage, UtilityPage } from '@/components/intentlock-app'
import PlatformDashboard from '@/components/dashboard/platform-dashboard'
import { AttackLabConsole, PaymentSetupConsole, RecoveryConsole, ReferenceBuyerConsole } from '@/components/console/commerce-operations'
import { OnboardingWorkspace } from '@/components/onboarding-workspace'
import { ConsoleGuard, OnboardingGuard } from '@/components/auth-guard'
import { LoginPage, RegisterPage } from '@/components/auth-pages'

export default async function Page({ params }: { params: Promise<{ slug: string[] }> }) {
  const { slug } = await params
  const path = `/${slug.join('/')}`
  if (path === '/login') return <LoginPage />
  if (path === '/register') return <RegisterPage />
  if (path === '/onboard') return <OnboardingGuard><OnboardingWorkspace /></OnboardingGuard>
  if (path === '/buyer-demo') return <ConsoleGuard><ReferenceBuyerConsole /></ConsoleGuard>
  if (path === '/dashboard') return <ConsoleGuard><PlatformDashboard Shell={Shell} /></ConsoleGuard>
  if (path === '/catalog') return <ConsoleGuard><CatalogPage /></ConsoleGuard>
  if (path === '/transactions') return <ConsoleGuard><TransactionsPage /></ConsoleGuard>
  if (path.startsWith('/transactions/')) return <ConsoleGuard><DetailPage id={slug[1]} /></ConsoleGuard>
  if (path.startsWith('/recovery/')) return <ConsoleGuard><DetailPage id={slug[1]} recovery /></ConsoleGuard>
  if (path === '/policies') return <ConsoleGuard><PolicyPage /></ConsoleGuard>
  if (path === '/attack-lab') return <ConsoleGuard><AttackLabConsole /></ConsoleGuard>
  if (path === '/recovery') return <ConsoleGuard><RecoveryConsole /></ConsoleGuard>
  if (path === '/payment-setup') return <ConsoleGuard><PaymentSetupConsole /></ConsoleGuard>
  if (['agents','audit','audit-log'].includes(slug[0] ?? '')) return <ConsoleGuard><UtilityPage page={slug[0]} /></ConsoleGuard>
  return <PublicHome />
}
