import { APP_NAME } from '../config';
import type { PageId } from '../hooks/useHashPage';
import { Icon } from './Icon';

interface NavItem {
  label: string;
  icon: string;
  /** Items without a page are not built yet (see the roadmap). */
  page?: PageId;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', icon: 'dashboard', page: 'overview' },
  { label: 'Transactions', icon: 'receipt_long' },
  { label: 'Forecast', icon: 'trending_up' },
  { label: 'Categories', icon: 'category' },
  { label: 'Model evaluation', icon: 'model_training', page: 'model' },
];

export function Sidebar({ active }: { active: PageId }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand__logo">
          <Icon name="account_balance_wallet" size={22} />
        </div>
        <div className="brand__text">
          <span className="brand__name">{APP_NAME}</span>
          <span className="brand__tag">Personal Ledger</span>
        </div>
      </div>

      <nav className="nav" aria-label="Main">
        {NAV_ITEMS.map((item) => {
          if (!item.page) {
            return (
              <span key={item.label} className="nav__item nav__item--disabled" aria-disabled="true">
                <Icon name={item.icon} />
                <span>{item.label}</span>
                <span className="nav__soon">Soon</span>
              </span>
            );
          }
          const isActive = item.page === active;
          return (
            <a
              key={item.label}
              className={`nav__item${isActive ? ' nav__item--active' : ''}`}
              href={`#${item.page}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </a>
          );
        })}
      </nav>
    </aside>
  );
}
