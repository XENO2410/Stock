import DailyGoalPanel from "@/components/DailyGoalPanel";
import Watchlist from "@/components/Watchlist";
import TopSignals from "@/components/TopSignals";
import MarketOverviewCard from "@/components/MarketOverviewCard";

export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <DailyGoalPanel />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Watchlist />
        </div>
        <div className="space-y-4">
          <TopSignals />
          <MarketOverviewCard />
        </div>
      </div>
    </div>
  );
}
